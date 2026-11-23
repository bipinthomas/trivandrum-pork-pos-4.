from pathlib import Path

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
MAIN = ROOT / "MainActivity.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")

def once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)

backup_manager = r'''package com.trivandrumpork.pos

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import com.trivandrumpork.pos.data.PosDatabase
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.InputStream
import java.io.OutputStream
import java.security.MessageDigest
import java.util.UUID
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

/**
 * Full offline POS backup.
 *
 * The ZIP contains the SQLite database, app-private files (including custom
 * product photos), shared preferences, a format manifest and a database hash.
 * Restore validates the complete archive and SQLite integrity before replacing
 * the current local data.
 */
object PosBackupManager {
    private const val DATABASE_NAME = "trivandrum_pork_pos.db"
    private const val BACKUP_FORMAT = "TRIVANDRUM_PORK_POS_BACKUP"
    private const val FORMAT_VERSION = 1
    private const val MAX_ENTRIES = 20000
    private const val MAX_UNCOMPRESSED_BYTES = 750L * 1024L * 1024L

    data class RestoreSummary(
        val productCount: Int,
        val billCount: Int,
        val createdAt: Long
    )

    fun createBackup(context: Context, helper: PosDatabase, output: OutputStream) {
        val database = helper.writableDatabase
        database.rawQuery("PRAGMA wal_checkpoint(TRUNCATE)", null).use { cursor ->
            if (cursor.moveToFirst() && cursor.getInt(0) != 0) {
                throw IllegalStateException("The POS database is busy. Close other POS activity and retry.")
            }
        }

        val productCount = countRows(database, "products")
        val billCount = countRows(database, "bills")
        val createdAt = System.currentTimeMillis()

        // Closing the helper flushes SQLite's WAL before the database file is copied.
        helper.close()
        val liveDatabase = context.getDatabasePath(DATABASE_NAME)
        check(liveDatabase.isFile && liveDatabase.length() > 0L) {
            "The POS database file was not found."
        }

        val temporaryRoot = File(context.cacheDir, "pos-backup-" + UUID.randomUUID()).apply {
            check(mkdirs() || isDirectory) { "Could not prepare a temporary backup folder." }
        }
        val databaseSnapshot = File(temporaryRoot, DATABASE_NAME)

        try {
            liveDatabase.copyTo(databaseSnapshot, overwrite = true)
            val manifest = JSONObject()
                .put("format", BACKUP_FORMAT)
                .put("formatVersion", FORMAT_VERSION)
                .put("databaseName", DATABASE_NAME)
                .put("createdAt", createdAt)
                .put("productCount", productCount)
                .put("billCount", billCount)
                .put("databaseSha256", sha256(databaseSnapshot))

            ZipOutputStream(BufferedOutputStream(output)).use { zip ->
                zip.putNextEntry(ZipEntry("manifest.json"))
                zip.write(manifest.toString().toByteArray(Charsets.UTF_8))
                zip.closeEntry()

                addFile(zip, databaseSnapshot, "database/" + DATABASE_NAME)
                addDirectory(zip, "files/")
                addDirectory(zip, "shared_prefs/")
                addTree(zip, context.filesDir, "files")
                val preferences = File(context.applicationInfo.dataDir, "shared_prefs")
                if (preferences.isDirectory) addTree(zip, preferences, "shared_prefs")
            }
        } finally {
            temporaryRoot.deleteRecursively()
        }
    }

    fun restoreBackup(context: Context, helper: PosDatabase, input: InputStream): RestoreSummary {
        val stage = File(context.cacheDir, "pos-restore-" + UUID.randomUUID()).apply {
            check(mkdirs() || isDirectory) { "Could not prepare a temporary restore folder." }
        }

        try {
            extractAndValidatePaths(input, stage)
            val manifestFile = File(stage, "manifest.json")
            check(manifestFile.isFile) { "This file is not a Trivandrum Pork POS backup." }
            val manifest = JSONObject(manifestFile.readText(Charsets.UTF_8))
            check(manifest.optString("format") == BACKUP_FORMAT) {
                "This backup file belongs to a different app."
            }
            check(manifest.optInt("formatVersion", -1) == FORMAT_VERSION) {
                "This backup format is not supported by this app version."
            }
            check(manifest.optString("databaseName") == DATABASE_NAME) {
                "The backup database does not match this POS app."
            }

            val stagedDatabase = File(stage, "database/" + DATABASE_NAME)
            check(stagedDatabase.isFile && stagedDatabase.length() > 0L) {
                "The backup does not contain the POS database."
            }
            check(sha256(stagedDatabase).equals(manifest.optString("databaseSha256"), true)) {
                "The backup database failed its integrity hash check."
            }
            verifySqliteDatabase(stagedDatabase)

            val summary = RestoreSummary(
                productCount = manifest.optInt("productCount", 0),
                billCount = manifest.optInt("billCount", 0),
                createdAt = manifest.optLong("createdAt", 0L)
            )

            val liveDatabase = context.getDatabasePath(DATABASE_NAME)
            val databaseDirectory = liveDatabase.parentFile
                ?: error("The app database folder is unavailable.")
            val stagedLiveDatabase = File(databaseDirectory, DATABASE_NAME + ".restore")
            val previousDatabase = File(databaseDirectory, DATABASE_NAME + ".previous")

            stagedDatabase.copyTo(stagedLiveDatabase, overwrite = true)

            val filesDestination = context.filesDir
            val preferencesDestination = File(context.applicationInfo.dataDir, "shared_prefs")
            val roots = listOf(
                "files" to filesDestination,
                "shared_prefs" to preferencesDestination
            )
            val previousRoots = roots.map { (key, destination) ->
                val snapshot = File(stage, "previous-" + key)
                if (destination.isDirectory) copyDirectoryContents(destination, snapshot)
                key to snapshot
            }.toMap()

            helper.close()
            deleteSqliteSidecars(liveDatabase)
            previousDatabase.delete()
            if (liveDatabase.exists()) {
                check(liveDatabase.renameTo(previousDatabase)) {
                    "Could not safely stage the existing POS database."
                }
            }

            if (!stagedLiveDatabase.renameTo(liveDatabase)) {
                if (previousDatabase.exists()) previousDatabase.renameTo(liveDatabase)
                throw IllegalStateException("Could not install the database from the selected backup.")
            }

            try {
                roots.forEach { (key, destination) ->
                    val source = File(stage, key)
                    clearDirectoryContents(destination)
                    if (source.isDirectory) copyDirectoryContents(source, destination)
                }
            } catch (restoreError: Exception) {
                // Roll back the database and private files if a file copy fails.
                liveDatabase.delete()
                if (previousDatabase.exists()) previousDatabase.renameTo(liveDatabase)
                roots.forEach { (key, destination) ->
                    clearDirectoryContents(destination)
                    val snapshot = previousRoots[key]
                    if (snapshot != null && snapshot.isDirectory) {
                        copyDirectoryContents(snapshot, destination)
                    }
                }
                throw restoreError
            }

            previousDatabase.delete()
            deleteSqliteSidecars(liveDatabase)
            return summary
        } finally {
            stage.deleteRecursively()
        }
    }

    private fun countRows(database: android.database.sqlite.SQLiteDatabase, table: String): Int {
        return database.rawQuery("SELECT COUNT(*) FROM " + table, null).use { cursor ->
            if (cursor.moveToFirst()) cursor.getInt(0) else 0
        }
    }

    private fun verifySqliteDatabase(file: File) {
        val database = SQLiteDatabase.openDatabase(
            file.absolutePath,
            null,
            SQLiteDatabase.OPEN_READONLY
        )
        try {
            val valid = database.rawQuery("PRAGMA integrity_check", null).use { cursor ->
                cursor.moveToFirst() && cursor.getString(0).equals("ok", true)
            }
            check(valid) { "The selected backup contains a damaged POS database." }
        } finally {
            database.close()
        }
    }

    private fun extractAndValidatePaths(input: InputStream, stage: File) {
        var entryCount = 0
        var totalBytes = 0L
        val canonicalRoot = stage.canonicalPath + File.separator

        ZipInputStream(BufferedInputStream(input)).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                entryCount += 1
                check(entryCount <= MAX_ENTRIES) { "The backup contains too many files." }

                val name = entry.name.replace('\\', '/')
                check(name.isNotBlank() && !name.startsWith("/") &&
                    !name.split('/').any { it == ".." || it == "." }) {
                    "The backup contains an unsafe file path."
                }
                check(
                    name == "manifest.json" ||
                    name.startsWith("database/") ||
                    name.startsWith("files/") ||
                    name.startsWith("shared_prefs/")
                ) { "The backup contains an unsupported file entry." }

                val destination = File(stage, name)
                check(destination.canonicalPath.startsWith(canonicalRoot)) {
                    "The backup contains an invalid file path."
                }

                if (entry.isDirectory) {
                    check(destination.mkdirs() || destination.isDirectory) {
                        "Could not extract a backup folder."
                    }
                } else {
                    destination.parentFile?.let { check(it.mkdirs() || it.isDirectory) }
                    destination.outputStream().buffered().use { output ->
                        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                        while (true) {
                            val count = zip.read(buffer)
                            if (count < 0) break
                            totalBytes += count
                            check(totalBytes <= MAX_UNCOMPRESSED_BYTES) {
                                "The backup is larger than the supported restore limit."
                            }
                            output.write(buffer, 0, count)
                        }
                    }
                }
                zip.closeEntry()
            }
        }
    }

    private fun addDirectory(zip: ZipOutputStream, path: String) {
        zip.putNextEntry(ZipEntry(path))
        zip.closeEntry()
    }

    private fun addTree(zip: ZipOutputStream, source: File, rootName: String) {
        if (!source.exists()) return
        source.walkTopDown().forEach { file ->
            if (file.isFile) {
                val relative = file.relativeTo(source).invariantSeparatorsPath
                if (relative.isNotBlank()) addFile(zip, file, rootName + "/" + relative)
            }
        }
    }

    private fun addFile(zip: ZipOutputStream, file: File, entryName: String) {
        zip.putNextEntry(ZipEntry(entryName))
        FileInputStream(file).buffered().use { it.copyTo(zip) }
        zip.closeEntry()
    }

    private fun copyDirectoryContents(source: File, destination: File) {
        if (!source.exists()) return
        check(destination.mkdirs() || destination.isDirectory) {
            "Could not prepare a restore folder."
        }
        source.listFiles()?.forEach { child ->
            val target = File(destination, child.name)
            if (child.isDirectory) {
                copyDirectoryContents(child, target)
            } else if (child.isFile) {
                target.parentFile?.mkdirs()
                child.copyTo(target, overwrite = true)
            }
        }
    }

    private fun clearDirectoryContents(directory: File) {
        if (!directory.exists()) {
            check(directory.mkdirs() || directory.isDirectory)
            return
        }
        directory.listFiles()?.forEach { child ->
            check(child.deleteRecursively()) { "Could not replace the app's saved files." }
        }
    }

    private fun deleteSqliteSidecars(database: File) {
        listOf("-wal", "-shm", "-journal").forEach { suffix ->
            File(database.absolutePath + suffix).delete()
        }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).buffered().use { input ->
            val buffer = ByteArray(32 * 1024)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
'''
(ROOT / "PosBackupManager.kt").write_text(backup_manager)

main = MAIN.read_text()
main = once(main, "import android.net.Uri\n",
    "import android.net.Uri\nimport android.os.Handler\nimport android.os.Looper\n",
    "backup main-thread imports")

screen = r'''@Composable
private fun BackupRestoreCard(
    busy: Boolean,
    onBackup: () -> Unit,
    onRestore: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.fillMaxWidth().padding(15.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text("Backup & Restore", fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
            Text(
                "Create one ZIP backup containing all bills, menu items, categories, discounts, business settings and custom product photos. Keep the file outside your phone so it is available after reinstalling the app.",
                color = Muted, fontSize = 12.sp, lineHeight = 18.sp
            )
            Button(
                onClick = onBackup,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth().height(50.dp),
                colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink),
                shape = RoundedCornerShape(12.dp)
            ) { Text("Create Full Backup", fontWeight = FontWeight.ExtraBold) }
            OutlinedButton(
                onClick = onRestore,
                enabled = !busy,
                modifier = Modifier.fillMaxWidth().height(50.dp),
                shape = RoundedCornerShape(12.dp)
            ) { Text("Restore from Backup File", fontWeight = FontWeight.Bold) }
            if (busy) Text("Processing backup. Keep the app open…", color = Green, fontSize = 12.sp)
            Text(
                "Restore replaces the data currently on this phone with the data in the selected backup. Export a fresh backup before restoring over existing records.",
                color = Muted, fontSize = 11.sp, lineHeight = 16.sp
            )
        }
    }
}

'''
main = once(main, "@Composable\nprivate fun SettingsScreen(",
    screen + "@Composable\nprivate fun SettingsScreen(",
    "insert backup and restore settings card")
main = once(main,
    "private fun SettingsScreen(settings: BusinessSettings, onSave: (BusinessSettings) -> Unit) {",
    "private fun SettingsScreen(settings: BusinessSettings, onSave: (BusinessSettings) -> Unit, onBackup: () -> Unit, onRestore: () -> Unit, backupBusy: Boolean) {",
    "settings screen backup callbacks")
main = once(main,
    '        if (formError.isNotBlank()) Text(formError, color = Red, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)',
    '        BackupRestoreCard(busy = backupBusy, onBackup = onBackup, onRestore = onRestore)\n        if (formError.isNotBlank()) Text(formError, color = Red, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)',
    "show backup restore card")

refresh_start = main.find("    fun refresh() {")
share_start = main.find("\n    fun shareBill", refresh_start)
if refresh_start < 0 or share_start < 0:
    raise SystemExit("Could not locate the POS refresh/share helpers for backup integration.")
refresh_block = main[refresh_start:share_start]
if "categoryDiscounts = db.getCategoryDiscounts()" not in refresh_block:
    raise SystemExit("The expected v1.3 refresh block was not found; refusing a partial backup integration.")

backup_callbacks = r'''
    var backupBusy by remember { mutableStateOf(false) }
    val backupHandler = remember { Handler(Looper.getMainLooper()) }

    val backupLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/zip")
    ) { uri: Uri? ->
        if (uri == null) {
            backupBusy = false
        } else {
            backupBusy = true
            Thread {
                try {
                    val output = context.contentResolver.openOutputStream(uri)
                        ?: error("Could not open the selected backup destination.")
                    output.use { PosBackupManager.createBackup(context, db, it) }
                    backupHandler.post {
                        backupBusy = false
                        Toast.makeText(context, "Full POS backup saved successfully.", Toast.LENGTH_LONG).show()
                    }
                } catch (e: Exception) {
                    backupHandler.post {
                        backupBusy = false
                        Toast.makeText(context, "Backup failed: " + (e.localizedMessage ?: "Unknown error"), Toast.LENGTH_LONG).show()
                    }
                }
            }.start()
        }
    }

    val restoreLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        if (uri == null) {
            backupBusy = false
        } else {
            backupBusy = true
            Thread {
                try {
                    val input = context.contentResolver.openInputStream(uri)
                        ?: error("Could not read the selected backup file.")
                    val restored = input.use { PosBackupManager.restoreBackup(context, db, it) }
                    backupHandler.post {
                        refresh()
                        backupBusy = false
                        Toast.makeText(
                            context,
                            "Restore complete: " + restored.billCount + " bills and " +
                                restored.productCount + " menu items recovered.",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                } catch (e: Exception) {
                    backupHandler.post {
                        backupBusy = false
                        Toast.makeText(context, "Restore failed: " + (e.localizedMessage ?: "Unknown error"), Toast.LENGTH_LONG).show()
                    }
                }
            }.start()
        }
    }

    fun startBackup() {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmm", Locale.ENGLISH).format(Date())
        backupLauncher.launch("TrivandrumPork_Backup_" + stamp + ".zip")
    }

    fun startRestore() {
        restoreLauncher.launch(arrayOf("application/zip", "application/x-zip-compressed", "application/octet-stream", "*/*"))
    }
'''
main = main[:share_start] + "\n" + backup_callbacks + main[share_start:]

old_route = 'AppScreen.SETTINGS -> SettingsScreen(settings = settings, onSave = { updated -> db.saveSettings(updated); settings = updated; Toast.makeText(context, "Settings saved", Toast.LENGTH_SHORT).show() })'
new_route = 'AppScreen.SETTINGS -> SettingsScreen(settings = settings, onSave = { updated -> db.saveSettings(updated); settings = updated; Toast.makeText(context, "Settings saved", Toast.LENGTH_SHORT).show() }, onBackup = ::startBackup, onRestore = ::startRestore, backupBusy = backupBusy)'
main = once(main, old_route, new_route, "connect backup actions to Settings screen")
MAIN.write_text(main)

gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 4", "versionCode = 5", "app version code")
gradle = once(gradle, 'versionName = "1.4.0"', 'versionName = "1.5.0"', "app version name")
GRADLE.write_text(gradle)

assert (ROOT / "PosBackupManager.kt").is_file()
assert "ActivityResultContracts.CreateDocument(\"application/zip\")" in MAIN.read_text()
assert "ActivityResultContracts.OpenDocument()" in MAIN.read_text()
assert "Restore from Backup File" in MAIN.read_text()
assert "PosBackupManager.restoreBackup" in MAIN.read_text()
assert "PosBackupManager.createBackup" in MAIN.read_text()
assert 'versionName = "1.5.0"' in GRADLE.read_text()
print("v1.5.0 full offline backup and restore integration applied.")
