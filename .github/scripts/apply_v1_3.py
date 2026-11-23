from pathlib import Path

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
DATA = ROOT / "data" / "PosDatabase.kt"
MAIN = ROOT / "MainActivity.kt"
INVOICE = ROOT / "InvoiceImageGenerator.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts"

)
def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match; found {count}")
    return text.replace(old, new, 1)

def between(text, start_marker, end_marker, replacement, label):
    start = text.find(start_marker)
    end = text.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"{label}: replacement boundary not found")
    return text[:start] + replacement + text[end:]

database = r'''package com.trivandrumpork.pos.data

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

data class Product(
    val id: Long = 0,
    val name: String,
    val category: String,
    val price: Int,
    val description: String = "",
    val active: Boolean = true,
    val imageRef: String = ""
)

data class BillLine(
    val productName: String,
    val quantity: Int,
    val unitPrice: Int,
    val originalUnitPrice: Int = unitPrice,
    val discountPercent: Int = 0,
    val category: String = ""
) {
    val amount: Int get() = quantity * unitPrice
    val originalAmount: Int get() = quantity * originalUnitPrice
    val discountAmount: Int get() = (originalUnitPrice - unitPrice).coerceAtLeast(0) * quantity
}

data class Bill(
    val id: Long,
    val billNo: String,
    val customerName: String,
    val mobile: String,
    val total: Int,
    val createdAt: Long,
    val items: List<BillLine>
) {
    val totalSavings: Int get() = items.sumOf { it.discountAmount }
    val originalTotal: Int get() = items.sumOf { it.originalAmount }
}

data class BusinessSettings(
    val businessName: String = "Trivandrum Pork",
    val contactNumber: String = "9847012345",
    val location: String = "Narikkal – Kattaikonam, Trivandrum",
    val tagline: String = "Only for the Real Pork Lovers!",
    val billPrefix: String = "TP"
)

class PosDatabase(context: Context) : SQLiteOpenHelper(context, DB_NAME, null, DB_VERSION) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("""CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            image_ref TEXT NOT NULL DEFAULT ''
        )""".trimIndent())
        db.execSQL("""CREATE TABLE bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT NOT NULL UNIQUE,
            customer_name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            total INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )""".trimIndent())
        db.execSQL("""CREATE TABLE bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            original_unit_price INTEGER NOT NULL DEFAULT 0,
            discount_percent INTEGER NOT NULL DEFAULT 0,
            category TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE
        )""".trimIndent())
        db.execSQL("CREATE TABLE settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")
        createCategoryTables(db)
        seedProducts(db)
        db.execSQL("INSERT OR IGNORE INTO categories(name) SELECT DISTINCT category FROM products WHERE TRIM(category) <> ''")
        db.execSQL("INSERT OR IGNORE INTO categories(name) VALUES('Other')")
    }

    private fun createCategoryTables(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY COLLATE NOCASE)")
        db.execSQL("CREATE TABLE IF NOT EXISTS category_discounts (category TEXT PRIMARY KEY COLLATE NOCASE, percentage INTEGER NOT NULL DEFAULT 0)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        if (oldVersion < 2) {
            createCategoryTables(db)
            db.execSQL("ALTER TABLE bill_items ADD COLUMN original_unit_price INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN category TEXT NOT NULL DEFAULT ''")
            db.execSQL("UPDATE bill_items SET original_unit_price = unit_price WHERE original_unit_price = 0")
            db.execSQL("INSERT OR IGNORE INTO categories(name) SELECT DISTINCT category FROM products WHERE TRIM(category) <> ''")
            db.execSQL("INSERT OR IGNORE INTO categories(name) VALUES('Other')")
        }
    }

    private fun seedProducts(db: SQLiteDatabase) {
        val defaults = listOf(
            Product(name = "Pork Vindaloo", category = "Vindaloo", price = 240, description = "Classic Kerala style pork vindaloo with rich spices.", imageRef = "pork_vindaloo"),
            Product(name = "Pork Roast", category = "Roast", price = 200, description = "Slow-roasted pork with traditional spices.", imageRef = "pork_roast"),
            Product(name = "Pork Fry", category = "Fry", price = 200, description = "Kerala style spicy pork fry.", imageRef = "pork_fry")
        )
        defaults.forEach { product ->
            val values = ContentValues().apply {
                put("name", product.name); put("category", product.category); put("price", product.price)
                put("description", product.description); put("active", 1); put("image_ref", product.imageRef)
            }
            db.insert("products", null, values)
        }
    }

    fun getProducts(includeInactive: Boolean = true): List<Product> {
        val result = mutableListOf<Product>()
        val where = if (includeInactive) null else "active=1"
        readableDatabase.query("products", null, where, null, null, null, "id ASC").use { c ->
            while (c.moveToNext()) result += Product(
                id = c.getLong(c.getColumnIndexOrThrow("id")),
                name = c.getString(c.getColumnIndexOrThrow("name")),
                category = c.getString(c.getColumnIndexOrThrow("category")),
                price = c.getInt(c.getColumnIndexOrThrow("price")),
                description = c.getString(c.getColumnIndexOrThrow("description")),
                active = c.getInt(c.getColumnIndexOrThrow("active")) == 1,
                imageRef = c.getString(c.getColumnIndexOrThrow("image_ref"))
            )
        }
        return result
    }

    fun getCategories(): List<String> {
        val db = writableDatabase
        db.insertWithOnConflict("categories", null, ContentValues().apply { put("name", "Other") }, SQLiteDatabase.CONFLICT_IGNORE)
        db.execSQL("INSERT OR IGNORE INTO categories(name) SELECT DISTINCT category FROM products WHERE TRIM(category) <> ''")
        val result = mutableListOf<String>()
        db.query("categories", arrayOf("name"), null, null, null, null, "name COLLATE NOCASE ASC").use { c ->
            while (c.moveToNext()) result += c.getString(0)
        }
        return result
    }

    fun addCategory(name: String): Boolean {
        val clean = name.trim()
        if (clean.isBlank() || clean.length > 32) return false
        return writableDatabase.insertWithOnConflict("categories", null, ContentValues().apply { put("name", clean) }, SQLiteDatabase.CONFLICT_IGNORE) != -1L
    }

    fun renameCategory(oldName: String, newName: String): Boolean {
        val oldClean = oldName.trim()
        val newClean = newName.trim()
        if (oldClean.isBlank() || newClean.isBlank() || newClean.length > 32 || oldClean.equals("Other", true)) return false
        if (oldClean.equals(newClean, true)) return true
        val db = writableDatabase
        val exists = db.rawQuery("SELECT COUNT(*) FROM categories WHERE name=? COLLATE NOCASE", arrayOf(newClean)).use { c ->
            c.moveToFirst() && c.getInt(0) > 0
        }
        if (exists) return false
        db.beginTransaction()
        try {
            val discount = db.rawQuery("SELECT percentage FROM category_discounts WHERE category=? COLLATE NOCASE", arrayOf(oldClean)).use { c ->
                if (c.moveToFirst()) c.getInt(0) else 0
            }
            db.update("products", ContentValues().apply { put("category", newClean) }, "category=? COLLATE NOCASE", arrayOf(oldClean))
            db.delete("category_discounts", "category=? COLLATE NOCASE", arrayOf(oldClean))
            db.delete("categories", "name=? COLLATE NOCASE", arrayOf(oldClean))
            db.insertOrThrow("categories", null, ContentValues().apply { put("name", newClean) })
            if (discount > 0) db.insertOrThrow("category_discounts", null, ContentValues().apply {
                put("category", newClean); put("percentage", discount)
            })
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }

    fun deleteCategory(name: String): Boolean {
        val clean = name.trim()
        if (clean.isBlank() || clean.equals("Other", true)) return false
        val db = writableDatabase
        db.beginTransaction()
        try {
            db.insertWithOnConflict("categories", null, ContentValues().apply { put("name", "Other") }, SQLiteDatabase.CONFLICT_IGNORE)
            db.update("products", ContentValues().apply { put("category", "Other") }, "category=? COLLATE NOCASE", arrayOf(clean))
            db.delete("category_discounts", "category=? COLLATE NOCASE", arrayOf(clean))
            db.delete("categories", "name=? COLLATE NOCASE", arrayOf(clean))
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }

    fun getCategoryDiscounts(): Map<String, Int> {
        val result = mutableMapOf<String, Int>()
        readableDatabase.query("category_discounts", arrayOf("category", "percentage"), null, null, null, null, null).use { c ->
            while (c.moveToNext()) result[c.getString(0)] = c.getInt(1)
        }
        return result
    }

    fun saveCategoryDiscount(category: String, percentage: Int) {
        val clean = category.trim()
        require(clean.isNotBlank() && percentage in 0..100)
        addCategory(clean)
        if (percentage == 0) {
            writableDatabase.delete("category_discounts", "category=? COLLATE NOCASE", arrayOf(clean))
        } else {
            writableDatabase.insertWithOnConflict(
                "category_discounts", null,
                ContentValues().apply { put("category", clean); put("percentage", percentage) },
                SQLiteDatabase.CONFLICT_REPLACE
            )
        }
    }

    fun saveProduct(product: Product): Long {
        addCategory(product.category)
        val values = ContentValues().apply {
            put("name", product.name.trim()); put("category", product.category.trim()); put("price", product.price)
            put("description", product.description.trim()); put("active", if (product.active) 1 else 0)
            put("image_ref", product.imageRef)
        }
        return if (product.id == 0L) writableDatabase.insert("products", null, values) else {
            writableDatabase.update("products", values, "id=?", arrayOf(product.id.toString())).toLong().let { product.id }
        }
    }

    fun setProductActive(id: Long, active: Boolean) {
        writableDatabase.update("products", ContentValues().apply { put("active", if (active) 1 else 0) }, "id=?", arrayOf(id.toString()))
    }

    fun deleteProduct(id: Long) {
        writableDatabase.delete("products", "id=?", arrayOf(id.toString()))
    }

    fun saveBill(customerName: String, mobile: String, lines: List<BillLine>, settings: BusinessSettings): Long {
        require(lines.isNotEmpty())
        val db = writableDatabase
        db.beginTransaction()
        try {
            val next = db.rawQuery("SELECT COUNT(*) FROM bills", null).use { c -> if (c.moveToFirst()) c.getInt(0) + 1 else 1 }
            val billNo = settings.billPrefix + next.toString().padStart(6, '0')
            val total = lines.sumOf { it.amount }
            val values = ContentValues().apply {
                put("bill_no", billNo); put("customer_name", customerName.trim()); put("mobile", mobile.trim())
                put("total", total); put("created_at", System.currentTimeMillis())
            }
            val billId = db.insertOrThrow("bills", null, values)
            lines.forEach { line ->
                val item = ContentValues().apply {
                    put("bill_id", billId); put("product_name", line.productName)
                    put("quantity", line.quantity); put("unit_price", line.unitPrice)
                    put("original_unit_price", line.originalUnitPrice); put("discount_percent", line.discountPercent)
                    put("category", line.category)
                }
                db.insertOrThrow("bill_items", null, item)
            }
            db.setTransactionSuccessful()
            return billId
        } finally {
            db.endTransaction()
        }
    }

    fun getBills(limit: Int = 250): List<Bill> = queryBills(null, null, "created_at DESC", limit)

    fun getBillsBetween(fromMillis: Long, toMillis: Long): List<Bill> =
        queryBills("created_at>=? AND created_at<=?", arrayOf(fromMillis.toString(), toMillis.toString()), "created_at ASC", null)

    private fun queryBills(selection: String?, args: Array<String>?, orderBy: String, limit: Int?): List<Bill> {
        val summaries = mutableListOf<Bill>()
        readableDatabase.query("bills", null, selection, args, null, null, orderBy, limit?.toString()).use { c ->
            while (c.moveToNext()) {
                val id = c.getLong(c.getColumnIndexOrThrow("id"))
                summaries += Bill(
                    id = id, billNo = c.getString(c.getColumnIndexOrThrow("bill_no")),
                    customerName = c.getString(c.getColumnIndexOrThrow("customer_name")),
                    mobile = c.getString(c.getColumnIndexOrThrow("mobile")),
                    total = c.getInt(c.getColumnIndexOrThrow("total")),
                    createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                    items = getBillLines(id)
                )
            }
        }
        return summaries
    }

    fun getBill(id: Long): Bill? {
        val summary = readableDatabase.query("bills", null, "id=?", arrayOf(id.toString()), null, null, null).use { c ->
            if (!c.moveToFirst()) return null
            Bill(
                id = c.getLong(c.getColumnIndexOrThrow("id")),
                billNo = c.getString(c.getColumnIndexOrThrow("bill_no")),
                customerName = c.getString(c.getColumnIndexOrThrow("customer_name")),
                mobile = c.getString(c.getColumnIndexOrThrow("mobile")),
                total = c.getInt(c.getColumnIndexOrThrow("total")),
                createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                items = emptyList()
            )
        }
        return summary.copy(items = getBillLines(id))
    }

    private fun getBillLines(billId: Long): List<BillLine> {
        val lines = mutableListOf<BillLine>()
        readableDatabase.query("bill_items", null, "bill_id=?", arrayOf(billId.toString()), null, null, "id ASC").use { c ->
            while (c.moveToNext()) {
                val unitPrice = c.getInt(c.getColumnIndexOrThrow("unit_price"))
                val original = c.getInt(c.getColumnIndexOrThrow("original_unit_price")).let { if (it > 0) it else unitPrice }
                lines += BillLine(
                    productName = c.getString(c.getColumnIndexOrThrow("product_name")),
                    quantity = c.getInt(c.getColumnIndexOrThrow("quantity")),
                    unitPrice = unitPrice,
                    originalUnitPrice = original,
                    discountPercent = c.getInt(c.getColumnIndexOrThrow("discount_percent")),
                    category = c.getString(c.getColumnIndexOrThrow("category"))
                )
            }
        }
        return lines
    }

    fun getSales(fromMillis: Long): Pair<Int, Int> {
        readableDatabase.rawQuery("SELECT COALESCE(SUM(total),0), COUNT(*) FROM bills WHERE created_at>=?", arrayOf(fromMillis.toString())).use { c ->
            if (c.moveToFirst()) return c.getInt(0) to c.getInt(1)
        }
        return 0 to 0
    }

    fun getSettings(): BusinessSettings {
        val values = mutableMapOf<String, String>()
        readableDatabase.query("settings", null, null, null, null, null, null).use { c ->
            while (c.moveToNext()) values[c.getString(0)] = c.getString(1)
        }
        return BusinessSettings(
            businessName = values["businessName"] ?: "Trivandrum Pork",
            contactNumber = values["contactNumber"] ?: "9847012345",
            location = values["location"] ?: "Narikkal – Kattaikonam, Trivandrum",
            tagline = values["tagline"] ?: "Only for the Real Pork Lovers!",
            billPrefix = values["billPrefix"] ?: "TP"
        )
    }

    fun saveSettings(settings: BusinessSettings) {
        val values = mapOf(
            "businessName" to settings.businessName,
            "contactNumber" to settings.contactNumber,
            "location" to settings.location,
            "tagline" to settings.tagline,
            "billPrefix" to settings.billPrefix
        )
        values.forEach { (key, value) ->
            val row = ContentValues().apply { put("setting_key", key); put("setting_value", value) }
            writableDatabase.insertWithOnConflict("settings", null, row, SQLiteDatabase.CONFLICT_REPLACE)
        }
    }

    companion object {
        private const val DB_NAME = "trivandrum_pork_pos.db"
        private const val DB_VERSION = 2
    }
}
'''
DATA.write_text(database)

exporter = r'''package com.trivandrumpork.pos

import com.trivandrumpork.pos.data.Bill
import java.io.ByteArrayOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

object SalesExcelExporter {
    fun generate(title: String, fromMillis: Long, toMillis: Long, bills: List<Bill>): ByteArray {
        val dateFormat = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.ENGLISH)
        val rows = mutableListOf<List<Any?>>()
        val originalSales = bills.sumOf { it.originalTotal }
        val totalDiscount = bills.sumOf { it.totalSavings }
        val netSales = bills.sumOf { it.total }
        rows += listOf("TRIVANDRUM PORK - SALES REPORT")
        rows += listOf(title)
        rows += listOf("From", dateFormat.format(Date(fromMillis)))
        rows += listOf("To", dateFormat.format(Date(toMillis)))
        rows.add(emptyList())
        rows += listOf("Summary", "Value")
        rows += listOf("Total Bills", bills.size)
        rows += listOf("Original Sales", originalSales)
        rows += listOf("Total Discounts", totalDiscount)
        rows += listOf("Net Sales", netSales)
        rows.add(emptyList())
        rows += listOf("Bill No", "Date", "Customer", "Mobile", "Category", "Item", "Qty", "Original Rate", "Discount %", "Discounted Rate", "Original Amount", "Discount Amount", "Net Amount")
        bills.forEach { bill ->
            bill.items.forEach { line ->
                rows += listOf(bill.billNo, dateFormat.format(Date(bill.createdAt)), bill.customerName, bill.mobile,
                    line.category, line.productName, line.quantity, line.originalUnitPrice, line.discountPercent,
                    line.unitPrice, line.originalAmount, line.discountAmount, line.amount)
            }
        }
        val widths = listOf(18, 24, 24, 18, 18, 28, 10, 15, 12, 17, 18, 18, 18)
        val sheet = buildString {
            append("""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>""")
            append("""<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="12" topLeftCell="A13" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>""")
            append("<cols>")
            widths.forEachIndexed { index, width ->
                val column = index + 1
                append("""<col min="$column" max="$column" width="$width" customWidth="1"/>""")
            }
            append("</cols><sheetData>")
            rows.forEachIndexed { rowIndex, row ->
                val rowNumber = rowIndex + 1
                append("""<row r="$rowNumber">""")
                row.forEachIndexed { colIndex, value ->
                    if (value != null) append(cellXml(columnName(colIndex + 1) + rowNumber, value))
                }
                append("</row>")
            }
            append("</sheetData>")
            if (rows.size >= 13) append("<autoFilter ref=\"A13:M" + rows.size + "\"/>")
            append("</worksheet>")
        }
        val contentTypes = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>"""
        val rootRels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
        val workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sales Report" sheetId="1" r:id="rId1"/></sheets></workbook>"""
        val workbookRels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>"""
        return ByteArrayOutputStream().use { output ->
            ZipOutputStream(output).use { zip ->
                zip.addText("[Content_Types].xml", contentTypes)
                zip.addText("_rels/.rels", rootRels)
                zip.addText("xl/workbook.xml", workbook)
                zip.addText("xl/_rels/workbook.xml.rels", workbookRels)
                zip.addText("xl/worksheets/sheet1.xml", sheet)
            }
            output.toByteArray()
        }
    }

    private fun cellXml(reference: String, value: Any): String {
        if (value is Number) return """<c r="$reference" t="n"><v>$value</v></c>"""
        val escaped = escapeXml(value.toString())
        return """<c r="$reference" t="inlineStr"><is><t xml:space="preserve">$escaped</t></is></c>"""
    }

    private fun escapeXml(value: String): String = value
        .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace("\"", "&quot;").replace("'", "&apos;")

    private fun columnName(number: Int): String {
        var value = number
        val result = StringBuilder()
        while (value > 0) {
            val remainder = (value - 1) % 26
            result.insert(0, ('A'.code + remainder).toChar())
            value = (value - 1) / 26
        }
        return result.toString()
    }

    private fun ZipOutputStream.addText(path: String, text: String) {
        putNextEntry(ZipEntry(path))
        write(text.toByteArray(Charsets.UTF_8))
        closeEntry()
    }
}
'''
(ROOT / "SalesExcelExporter.kt").write_text(exporter)

main = MAIN.read_text()
main = once(main, "import androidx.compose.ui.text.style.TextOverflow\n",
    "import androidx.compose.ui.text.style.TextOverflow\nimport androidx.compose.ui.text.style.TextDecoration\n", "text decoration import")
main = once(main,
    "private enum class AppScreen { POS, BILLS, MENU, SALES, SETTINGS, ADD_ITEM, BILL_DETAIL }",
    """private enum class AppScreen { POS, BILLS, MENU, SALES, SETTINGS, ADD_ITEM, BILL_DETAIL }
private enum class SalesReportPeriod(val title: String, val fileTag: String) {
    DAILY("Daily Sales", "Daily"), MONTHLY("Monthly Sales", "Monthly"),
    HALF_YEARLY("Half-Yearly Sales", "HalfYearly"), YEARLY("Yearly Sales", "Yearly")
}
private fun discountedUnitPrice(originalPrice: Int, percentage: Int): Int {
    val safePercent = percentage.coerceIn(0, 100)
    return ((originalPrice.toLong() * (100 - safePercent) + 50L) / 100L).toInt()
}""",
    "report period and price helper")
main = once(main, "    var deleteCandidate by remember { mutableStateOf<Product?>(null) }\n",
    """    var deleteCandidate by remember { mutableStateOf<Product?>(null) }
    var categories by remember { mutableStateOf(db.getCategories()) }
    var categoryDiscounts by remember { mutableStateOf(db.getCategoryDiscounts()) }
    var pendingReportBytes by remember { mutableStateOf<ByteArray?>(null) }
    val reportLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    ) { uri ->
        if (uri != null) {
            try {
                val bytes = pendingReportBytes ?: error("Report data is no longer available")
                context.contentResolver.openOutputStream(uri)?.use { it.write(bytes) }
                    ?: error("Could not open the selected file")
                Toast.makeText(context, "Excel report exported successfully", Toast.LENGTH_LONG).show()
            } catch (e: Exception) {
                Toast.makeText(context, "Export failed: " + (e.localizedMessage ?: "Unknown error"), Toast.LENGTH_LONG).show()
            }
        }
        pendingReportBytes = null
    }
""", "category and report state")
main = once(main,
    """        settings = db.getSettings()
    }

    fun shareBill""",
    """        settings = db.getSettings()
        categories = db.getCategories()
        categoryDiscounts = db.getCategoryDiscounts()
    }

    fun exportSalesReport(period: SalesReportPeriod) {
        val range = Calendar.getInstance()
        val end = range.timeInMillis
        when (period) {
            SalesReportPeriod.DAILY -> Unit
            SalesReportPeriod.MONTHLY -> range.set(Calendar.DAY_OF_MONTH, 1)
            SalesReportPeriod.HALF_YEARLY -> {
                range.set(Calendar.MONTH, if (range.get(Calendar.MONTH) < Calendar.JULY) Calendar.JANUARY else Calendar.JULY)
                range.set(Calendar.DAY_OF_MONTH, 1)
            }
            SalesReportPeriod.YEARLY -> {
                range.set(Calendar.MONTH, Calendar.JANUARY)
                range.set(Calendar.DAY_OF_MONTH, 1)
            }
        }
        range.set(Calendar.HOUR_OF_DAY, 0); range.set(Calendar.MINUTE, 0)
        range.set(Calendar.SECOND, 0); range.set(Calendar.MILLISECOND, 0)
        val start = range.timeInMillis
        val reportBills = db.getBillsBetween(start, end)
        pendingReportBytes = SalesExcelExporter.generate(period.title, start, end, reportBills)
        val dateTag = SimpleDateFormat("yyyyMMdd", Locale.ENGLISH).format(Date(end))
        reportLauncher.launch("TrivandrumPork_" + period.fileTag + "_Sales_" + dateTag + ".xlsx")
    }

    fun shareBill""", "report export callback")
main = once(main,
    """                    AppScreen.POS -> PosScreen(
                        products = products.filter { it.active }, category = posCategory,""",
    """                    AppScreen.POS -> PosScreen(
                        products = products.filter { it.active }, categories = categories, discounts = categoryDiscounts, category = posCategory,""",
    "POS dynamic categories")
main = once(main,
    "                                if (product == null || qty < 1) null else BillLine(product.name, qty, product.price)",
    """                                if (product == null || qty < 1) null else {
                                    val percent = categoryDiscounts[product.category] ?: 0
                                    BillLine(productName = product.name, quantity = qty,
                                        unitPrice = discountedUnitPrice(product.price, percent),
                                        originalUnitPrice = product.price, discountPercent = percent, category = product.category)
                                }""", "discounted bill lines")

old_menu = """                    AppScreen.MENU -> MenuScreen(
                        products = products, category = menuCategory, onCategory = { menuCategory = it },
                        onAdd = { editProduct = null; screen = AppScreen.ADD_ITEM },
                        onEdit = { editProduct = it; screen = AppScreen.ADD_ITEM },
                        onToggle = { product, enabled -> db.setProductActive(product.id, enabled); refresh() },
                        onDelete = { deleteCandidate = it }
                    )"""
new_menu = """                    AppScreen.MENU -> MenuScreen(
                        products = products, categories = categories, discounts = categoryDiscounts,
                        category = menuCategory, onCategory = { menuCategory = it },
                        onAdd = { editProduct = null; screen = AppScreen.ADD_ITEM },
                        onEdit = { editProduct = it; screen = AppScreen.ADD_ITEM },
                        onToggle = { product, enabled -> db.setProductActive(product.id, enabled); refresh() },
                        onDelete = { deleteCandidate = it },
                        onAddCategory = { name -> val ok = db.addCategory(name); if (ok) refresh(); ok },
                        onRenameCategory = { oldName, newName ->
                            val ok = db.renameCategory(oldName, newName)
                            if (ok) {
                                if (menuCategory.equals(oldName, true)) menuCategory = newName
                                if (posCategory.equals(oldName, true)) posCategory = newName
                                refresh()
                            }
                            ok
                        },
                        onDeleteCategory = { name ->
                            db.deleteCategory(name)
                            if (menuCategory.equals(name, true)) menuCategory = "All"
                            if (posCategory.equals(name, true)) posCategory = "All"
                            refresh()
                        },
                        onSetDiscount = { name, percentage -> db.saveCategoryDiscount(name, percentage); refresh() }
                    )"""
main = once(main, old_menu, new_menu, "MenuScreen callback wiring")
main = once(main,
    """                        AddItemScreen(
                            product = editProduct,""",
    """                        AddItemScreen(
                            product = editProduct, categories = categories,""", "AddItemScreen category list")
main = once(main, "                    AppScreen.SALES -> SalesScreen(db = db, bills = bills)",
    "                    AppScreen.SALES -> SalesScreen(db = db, bills = bills, onExport = ::exportSalesReport)", "Sales export callback")

pos_screen = """@Composable
private fun PosScreen(
    products: List<Product>, categories: List<String>, discounts: Map<String, Int>,
    category: String, onCategory: (String) -> Unit,
    cart: Map<Long, Int>, customerName: String, onCustomerName: (String) -> Unit,
    mobile: String, onMobile: (String) -> Unit, onSave: () -> Unit,
    onAdd: (Long) -> Unit, onQuantity: (Long, Int) -> Unit, onClear: () -> Unit
) {
    val categoryOptions = listOf("All") + categories
    val columns = if (LocalConfiguration.current.screenWidthDp < 360) 2 else 3
    val filtered = if (category == "All") products else products.filter { it.category.equals(category, true) }
    val cartProducts = cart.entries.mapNotNull { entry -> products.firstOrNull { it.id == entry.key }?.let { it to entry.value } }
    val total = cartProducts.sumOf { (product, qty) -> discountedUnitPrice(product.price, discounts[product.category] ?: 0) * qty }
    val totalSavings = cartProducts.sumOf { (product, qty) -> (product.price - discountedUnitPrice(product.price, discounts[product.category] ?: 0)) * qty }

    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 11.dp)) {
        Text("Select Product", fontSize = 21.sp, fontWeight = FontWeight.ExtraBold, color = Ink)
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            categoryOptions.forEach { c -> CategoryChip(c, selected = category == c, onClick = { onCategory(c) }) }
        }
        Spacer(Modifier.height(12.dp))
        if (filtered.isEmpty()) EmptyState("No active products", "Add or activate products from the Menu screen")
        else {
            val rows = filtered.chunked(columns)
            rows.forEachIndexed { index, row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { product ->
                        ProductTile(product, selected = (cart[product.id] ?: 0) > 0,
                            discountPercent = discounts[product.category] ?: 0,
                            onAdd = { onAdd(product.id) }, modifier = Modifier.weight(1f))
                    }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
                if (index != rows.lastIndex) Spacer(Modifier.height(9.dp))
            }
        }
        Spacer(Modifier.height(15.dp))
        Card(modifier = Modifier.animateContentSize(), shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Order Cart", fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
                    Text(" (" + cartProducts.sumOf { it.second } + " items)", fontSize = 16.sp, color = Muted)
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onClear, enabled = cart.isNotEmpty()) {
                        Icon(Icons.Filled.Delete, null, tint = Red, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(3.dp)); Text("Clear", color = Red, fontWeight = FontWeight.Bold)
                    }
                }
                if (cartProducts.isEmpty()) Text("Your cart is empty. Tap + on a product to add it.", color = Muted, fontSize = 13.sp, modifier = Modifier.padding(vertical = 12.dp))
                else cartProducts.forEachIndexed { index, (product, qty) ->
                    CartLine(product, qty, discounts[product.category] ?: 0,
                        compact = LocalConfiguration.current.screenWidthDp < 390,
                        onMinus = { onQuantity(product.id, qty - 1) }, onPlus = { onQuantity(product.id, qty + 1) })
                    if (index != cartProducts.lastIndex) Divider(color = Line)
                }
                Spacer(Modifier.height(10.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(15.dp)).background(Cream).padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("Total Amount", fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                    Spacer(Modifier.weight(1f)); Text(rupees(total), fontSize = 28.sp, color = Red, fontWeight = FontWeight.ExtraBold)
                }
                if (totalSavings > 0) Text("You save " + rupees(totalSavings) + " with category discounts", color = Green, fontWeight = FontWeight.Bold, fontSize = 13.sp, modifier = Modifier.padding(top = 8.dp))
            }
        }
        Spacer(Modifier.height(16.dp))
        Text("Customer Details", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(start = 3.dp, bottom = 9.dp))
        if (LocalConfiguration.current.screenWidthDp < 375) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = customerName, onValueChange = onCustomerName, modifier = Modifier.fillMaxWidth(), label = { Text("Name") }, leadingIcon = { Icon(Icons.Filled.Person, null, tint = Muted) }, singleLine = true, shape = RoundedCornerShape(15.dp))
                OutlinedTextField(value = mobile, onValueChange = { onMobile(it.filter { ch -> ch.isDigit() || ch == '+' }.take(15)) }, modifier = Modifier.fillMaxWidth(), label = { Text("Mobile Number") }, leadingIcon = { Icon(Icons.Filled.Phone, null, tint = Muted) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(15.dp))
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(value = customerName, onValueChange = onCustomerName, modifier = Modifier.weight(1f), label = { Text("Name") }, leadingIcon = { Icon(Icons.Filled.Person, null, tint = Muted) }, singleLine = true, shape = RoundedCornerShape(15.dp))
                OutlinedTextField(value = mobile, onValueChange = { onMobile(it.filter { ch -> ch.isDigit() || ch == '+' }.take(15)) }, modifier = Modifier.weight(1f), label = { Text("Mobile Number") }, leadingIcon = { Icon(Icons.Filled.Phone, null, tint = Muted) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(15.dp))
            }
        }
        Spacer(Modifier.height(14.dp))
        Button(onClick = onSave, modifier = Modifier.fillMaxWidth().height(62.dp), shape = RoundedCornerShape(16.dp), colors = ButtonDefaults.buttonColors(containerColor = Green, contentColor = Color.White)) {
            Icon(Icons.Filled.Chat, contentDescription = "WhatsApp", modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(10.dp)); Text("Save & Send via WhatsApp", fontSize = if (LocalConfiguration.current.screenWidthDp < 380) 16.sp else 18.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(24.dp))
    }
}

"""
main = between(main, "@Composable\nprivate fun PosScreen(", "@Composable\nprivate fun CategoryChip", pos_screen, "POS screen")

product_tile = """@Composable
private fun ProductTile(product: Product, selected: Boolean, discountPercent: Int, onAdd: () -> Unit, modifier: Modifier = Modifier) {
    val tileColor by animateColorAsState(if (selected) Cream else Color.White, label = "product-tile-color")
    val tileBorder by animateColorAsState(if (selected) Yellow else Line, label = "product-tile-border")
    val tileElevation by animateDpAsState(if (selected) 4.dp else 2.dp, label = "product-tile-elevation")
    val salePrice = discountedUnitPrice(product.price, discountPercent)
    Card(modifier = modifier.height(if (LocalConfiguration.current.screenWidthDp < 360) 164.dp else 174.dp), onClick = onAdd,
        shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = tileColor),
        border = BorderStroke(if (selected) 1.5.dp else 1.dp, tileBorder), elevation = CardDefaults.cardElevation(tileElevation)) {
        Column(Modifier.fillMaxSize().padding(horizontal = 6.dp, vertical = 8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box {
                ProductImage(product, Modifier.size(76.dp).clip(RoundedCornerShape(13.dp)))
                if (selected) Box(Modifier.align(Alignment.TopEnd).padding(2.dp).size(20.dp).clip(CircleShape).background(Yellow), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.Check, null, tint = Ink, modifier = Modifier.size(14.dp))
                }
            }
            Text(product.name, fontSize = 14.sp, lineHeight = 16.sp, fontWeight = FontWeight.Bold, color = Ink, maxLines = 2, textAlign = TextAlign.Center, modifier = Modifier.weight(1f).padding(top = 5.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column {
                    if (discountPercent > 0) {
                        Text(rupees(product.price), color = Muted, fontSize = 11.sp, textDecoration = TextDecoration.LineThrough)
                        Text(discountPercent.toString() + "% OFF", color = Green, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                    }
                    Text(rupees(salePrice), color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                }
                Surface(onClick = onAdd, shape = CircleShape, color = Yellow, modifier = Modifier.size(36.dp)) {
                    Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.Add, null, tint = Ink, modifier = Modifier.size(23.dp)) }
                }
            }
        }
    }
}

"""
main = between(main, "@Composable\nprivate fun ProductTile(", "@Composable\nprivate fun ProductImage", product_tile, "discounted product tile")

cart_line = """@Composable
private fun CartLine(product: Product, quantity: Int, discountPercent: Int, compact: Boolean, onMinus: () -> Unit, onPlus: () -> Unit) {
    val salePrice = discountedUnitPrice(product.price, discountPercent)
    val amount = salePrice * quantity
    if (compact) {
        Row(Modifier.fillMaxWidth().heightIn(min = 62.dp).padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            Column(Modifier.weight(1f)) {
                Text(product.name, fontSize = 13.sp, fontWeight = FontWeight.Bold, maxLines = 2, lineHeight = 15.sp)
                if (discountPercent > 0) Text(rupees(product.price), fontSize = 11.sp, color = Muted, textDecoration = TextDecoration.LineThrough)
                Text(rupees(salePrice), fontSize = 12.sp, color = if (discountPercent > 0) Green else Muted, fontWeight = FontWeight.SemiBold)
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                SmallQuantityButton("−", false, onMinus)
                Box(Modifier.width(29.dp).height(32.dp).border(1.dp, Line, RoundedCornerShape(9.dp)), contentAlignment = Alignment.Center) {
                    Text(quantity.toString(), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                SmallQuantityButton("+", true, onPlus)
            }
            Text(rupees(amount), fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.End, modifier = Modifier.widthIn(min = 52.dp))
        }
    } else {
        Row(Modifier.fillMaxWidth().heightIn(min = 60.dp).padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1.25f)) {
                Text(product.name, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 2)
                if (discountPercent > 0) Text(rupees(product.price) + " → " + rupees(salePrice), fontSize = 11.sp, color = Green)
                else Text(rupees(salePrice), fontSize = 12.sp, color = Muted)
            }
            Row(Modifier.weight(1.55f), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                SmallQuantityButton("−", false, onMinus)
                Box(Modifier.padding(horizontal = 3.dp).width(35.dp).height(34.dp).border(1.dp, Line, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) {
                    Text(quantity.toString(), fontWeight = FontWeight.Bold, fontSize = 15.sp)
                }
                SmallQuantityButton("+", true, onPlus)
            }
            Text(rupees(amount), fontSize = 14.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.End, modifier = Modifier.weight(.75f))
        }
    }
}

"""
main = between(main, "@Composable\nprivate fun CartLine(", "@Composable\nprivate fun SmallQuantityButton", cart_line, "discounted cart line")

menu_screen = """@Composable
private fun MenuScreen(
    products: List<Product>, categories: List<String>, discounts: Map<String, Int>,
    category: String, onCategory: (String) -> Unit, onAdd: () -> Unit,
    onEdit: (Product) -> Unit, onToggle: (Product, Boolean) -> Unit, onDelete: (Product) -> Unit,
    onAddCategory: (String) -> Boolean, onRenameCategory: (String, String) -> Boolean,
    onDeleteCategory: (String) -> Unit, onSetDiscount: (String, Int) -> Unit
) {
    val menuContext = LocalContext.current
    val filtered = if (category == "All") products else products.filter { it.category.equals(category, true) }
    var categoryDialog by remember { mutableStateOf(false) }
    var editingCategory by remember { mutableStateOf<String?>(null) }
    var categoryName by remember { mutableStateOf("") }
    var categoryError by remember { mutableStateOf("") }
    var discountCategory by remember { mutableStateOf<String?>(null) }
    var discountValue by remember { mutableStateOf("0") }
    var deleteCategoryCandidate by remember { mutableStateOf<String?>(null) }

    LazyColumn(Modifier.fillMaxSize().padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        item {
            Row(Modifier.fillMaxWidth().padding(top = 13.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("Menu Items", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.weight(1f))
                Button(onClick = onAdd, colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink), shape = RoundedCornerShape(13.dp)) {
                    Icon(Icons.Filled.Add, null); Spacer(Modifier.width(3.dp)); Text("Add Item", fontWeight = FontWeight.Bold)
                }
            }
        }
        item {
            Card(shape = RoundedCornerShape(17.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text("Categories & Discounts", fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
                            Text("Discounts apply automatically to every item in that category", color = Muted, fontSize = 11.sp)
                        }
                        Button(onClick = {
                            editingCategory = null; categoryName = ""; categoryError = ""; categoryDialog = true
                        }, colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink), contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 10.dp, vertical = 6.dp)) {
                            Icon(Icons.Filled.Add, null, modifier = Modifier.size(17.dp)); Text("Add")
                        }
                    }
                    categories.forEach { name ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(name, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                                val percentage = discounts[name] ?: 0
                                Text(if (percentage > 0) percentage.toString() + "% discount applied" else "No category discount", color = if (percentage > 0) Green else Muted, fontSize = 11.sp)
                            }
                            TextButton(onClick = {
                                discountCategory = name; discountValue = (discounts[name] ?: 0).toString()
                            }, contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 6.dp)) {
                                Text("% OFF", color = Green, fontWeight = FontWeight.Bold)
                            }
                            if (!name.equals("Other", true)) {
                                IconButton(onClick = {
                                    editingCategory = name; categoryName = name; categoryError = ""; categoryDialog = true
                                }, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.Edit, "Edit category", tint = Navy, modifier = Modifier.size(18.dp)) }
                                IconButton(onClick = { deleteCategoryCandidate = name }, modifier = Modifier.size(34.dp)) {
                                    Icon(Icons.Filled.Delete, "Delete category", tint = Red, modifier = Modifier.size(18.dp))
                                }
                            }
                        }
                    }
                }
            }
        }
        item {
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                (listOf("All") + categories).forEach { CategoryChip(it, category == it) { onCategory(it) } }
            }
        }
        if (filtered.isEmpty()) item { EmptyState("No menu items", "Use Add Item to create your first product") }
        items(filtered, key = { it.id }) { product ->
            Card(shape = RoundedCornerShape(17.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
                Row(Modifier.fillMaxWidth().padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    ProductImage(product, Modifier.size(92.dp).clip(RoundedCornerShape(13.dp)))
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(product.name, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(product.category, fontSize = 13.sp, color = Muted)
                        val percentage = discounts[product.category] ?: 0
                        if (percentage > 0) {
                            Text(rupees(product.price), color = Muted, fontSize = 11.sp, textDecoration = TextDecoration.LineThrough)
                            Text(rupees(discountedUnitPrice(product.price, percentage)), color = Red, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                            Text(percentage.toString() + "% category discount", color = Green, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        } else Text(rupees(product.price), color = Red, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            IconButton(onClick = { onEdit(product) }, modifier = Modifier.size(32.dp)) { Icon(Icons.Filled.Edit, "Edit", tint = Navy, modifier = Modifier.size(19.dp)) }
                            TextButton(onClick = { onDelete(product) }, contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 3.dp)) {
                                Icon(Icons.Filled.Delete, null, tint = Red, modifier = Modifier.size(16.dp)); Text("Delete", color = Red, fontSize = 12.sp)
                            }
                        }
                    }
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Switch(checked = product.active, onCheckedChange = { onToggle(product, it) }, colors = androidx.compose.material3.SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Green, checkedBorderColor = Green))
                        Text(if (product.active) "Active" else "Off", fontSize = 11.sp, color = if (product.active) Green else Muted)
                    }
                }
            }
        }
        item {
            Row(Modifier.fillMaxWidth().padding(vertical = 10.dp).clip(RoundedCornerShape(14.dp)).background(Color(0xFFEAF0F4)).padding(16.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Total Items: " + products.size, fontWeight = FontWeight.Bold)
                Text("Active: " + products.count { it.active }, color = Green, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(20.dp))
        }
    }

    if (categoryDialog) AlertDialog(
        onDismissRequest = { categoryDialog = false },
        title = { Text(if (editingCategory == null) "Add Category" else "Edit Category") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(categoryName, { categoryName = it; categoryError = "" }, label = { Text("Category name") }, singleLine = true)
                if (categoryError.isNotBlank()) Text(categoryError, color = Red, fontSize = 12.sp)
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val ok = if (editingCategory == null) onAddCategory(categoryName) else onRenameCategory(editingCategory!!, categoryName)
                if (ok) categoryDialog = false else categoryError = "Enter a unique category name (maximum 32 characters)."
            }) { Text("Save") }
        },
        dismissButton = { TextButton(onClick = { categoryDialog = false }) { Text("Cancel") } }
    )

    discountCategory?.let { name ->
        AlertDialog(
            onDismissRequest = { discountCategory = null },
            title = { Text("Category discount") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Apply the same discount to every item in " + name + ".", color = Muted, fontSize = 13.sp)
                    OutlinedTextField(discountValue, { discountValue = it.filter(Char::isDigit).take(3) }, label = { Text("Discount percentage (0–100)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val value = discountValue.toIntOrNull()
                    if (value == null || value !in 0..100) Toast.makeText(menuContext, "Enter a percentage from 0 to 100", Toast.LENGTH_SHORT).show()
                    else { onSetDiscount(name, value); discountCategory = null }
                }) { Text("Apply") }
            },
            dismissButton = { TextButton(onClick = { discountCategory = null }) { Text("Cancel") } }
        )
    }

    deleteCategoryCandidate?.let { name ->
        AlertDialog(
            onDismissRequest = { deleteCategoryCandidate = null },
            title = { Text("Delete " + name + "?") },
            text = { Text("All products in this category will be moved to Other. Existing bills will remain unchanged.") },
            confirmButton = { TextButton(onClick = { onDeleteCategory(name); deleteCategoryCandidate = null }) { Text("Delete", color = Red) } },
            dismissButton = { TextButton(onClick = { deleteCategoryCandidate = null }) { Text("Cancel") } }
        )
    }
}

"""
main = between(main, "@Composable\nprivate fun MenuScreen(", "@Composable\nprivate fun AddItemScreen", menu_screen, "category manager UI")
main = once(main, "private fun AddItemScreen(product: Product?, onCancel: () -> Unit, onSave: (Product) -> Unit) {",
    "private fun AddItemScreen(product: Product?, categories: List<String>, onCancel: () -> Unit, onSave: (Product) -> Unit) {",
    "AddItemScreen signature")
main = once(main, 'var category by remember { mutableStateOf(product?.category ?: "Vindaloo") }',
    'var category by remember { mutableStateOf(product?.category ?: categories.firstOrNull() ?: "Other") }',
    "AddItemScreen default category")
main = once(main, '                listOf("Vindaloo", "Roast", "Fry", "Other").forEach { option ->',
    '                categories.forEach { option ->', "dynamic category options")
main = once(main,
    """                        Text(rupees(line.unitPrice), modifier = Modifier.weight(.7f), textAlign = TextAlign.End, fontSize = 13.sp)
                        Text(rupees(line.amount), modifier = Modifier.weight(.8f), textAlign = TextAlign.End, fontWeight = FontWeight.Bold, fontSize = 13.sp)""",
    """                        Column(Modifier.weight(.7f), horizontalAlignment = Alignment.End) {
                            if (line.discountAmount > 0) Text(rupees(line.originalUnitPrice), color = Muted, fontSize = 10.sp, textDecoration = TextDecoration.LineThrough)
                            Text(rupees(line.unitPrice), textAlign = TextAlign.End, fontSize = 13.sp, color = if (line.discountAmount > 0) Green else Ink, fontWeight = FontWeight.SemiBold)
                        }
                        Text(rupees(line.amount), modifier = Modifier.weight(.8f), textAlign = TextAlign.End, fontWeight = FontWeight.Bold, fontSize = 13.sp)""",
    "bill detail rate display")
main = once(main,
    """                Divider(Modifier.padding(vertical = 10.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Cream).padding(13.dp), verticalAlignment = Alignment.CenterVertically) {""",
    """                if (bill.totalSavings > 0) Text("You saved " + rupees(bill.totalSavings), color = Green, fontWeight = FontWeight.ExtraBold, fontSize = 15.sp)
                Divider(Modifier.padding(vertical = 10.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Cream).padding(13.dp), verticalAlignment = Alignment.CenterVertically) {""",
    "bill detail savings line")

sales_screen = """@Composable
private fun SalesScreen(db: PosDatabase, bills: List<Bill>, onExport: (SalesReportPeriod) -> Unit) {
    val todayStart = remember { Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
    }.timeInMillis }
    val monthStart = remember { Calendar.getInstance().apply {
        set(Calendar.DAY_OF_MONTH, 1); set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0)
    }.timeInMillis }
    val today = db.getSales(todayStart)
    val month = db.getSales(monthStart)
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Sales Overview", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("Today's Sales", rupees(today.first), today.second.toString() + " bills", Yellow, Modifier.weight(1f))
            MetricCard("This Month", rupees(month.first), month.second.toString() + " bills", Color(0xFFE8F3EB), Modifier.weight(1f))
        }
        Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.fillMaxWidth().padding(15.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Export Excel Report", fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                Text("Export a true .xlsx workbook with item sales, original rates, discounts and net sales.", color = Muted, fontSize = 12.sp)
                listOf(SalesReportPeriod.DAILY, SalesReportPeriod.MONTHLY, SalesReportPeriod.HALF_YEARLY, SalesReportPeriod.YEARLY).forEach { period ->
                    OutlinedButton(onClick = { onExport(period) }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) {
                        Icon(Icons.Filled.Share, null, tint = Green); Spacer(Modifier.width(8.dp))
                        Text("Export " + period.title, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
        Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.padding(16.dp)) {
                Text("Recent Transactions", fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                Spacer(Modifier.height(8.dp))
                if (bills.isEmpty()) Text("No sales recorded yet", color = Muted, modifier = Modifier.padding(vertical = 15.dp))
                else bills.take(8).forEach { bill ->
                    Row(Modifier.fillMaxWidth().padding(vertical = 9.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(bill.billNo, fontWeight = FontWeight.Bold)
                            Text(bill.customerName, color = Muted, fontSize = 12.sp)
                        }
                        Text(rupees(bill.total), fontWeight = FontWeight.ExtraBold, color = Red)
                    }
                    Divider(color = Line)
                }
            }
        }
        Spacer(Modifier.height(20.dp))
    }
}

"""
main = between(main, "@Composable\nprivate fun SalesScreen(", "@Composable\nprivate fun MetricCard", sales_screen, "Excel export screen")
MAIN.write_text(main)

invoice = INVOICE.read_text()
invoice = once(invoice,
    """        canvas.drawText("Item", 110f, tableTop + 47f, textPaint(31f, white, true))
        drawRight(canvas, "Qty", 682f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Price", 830f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Amount", 972f, tableTop + 47f, 29f, white, true)""",
    """        canvas.drawText("Item", 110f, tableTop + 47f, textPaint(31f, white, true))
        drawRight(canvas, "Qty", 682f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Rate", 830f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Amount", 972f, tableTop + 47f, 29f, white, true)""",
    "invoice table headings")
invoice = once(invoice,
    """            drawFitted(canvas, line.productName, 110f, rowY, 500f, 31f, black, true)
            drawRight(canvas, line.quantity.toString(), 682f, rowY, 30f, black, false)
            drawRight(canvas, rupees(line.unitPrice), 830f, rowY, 30f, black, false)
            drawRight(canvas, rupees(line.amount), 972f, rowY, 30f, black, true)""",
    """            drawFitted(canvas, line.productName, 110f, rowY, 500f, 31f, black, true)
            drawRight(canvas, line.quantity.toString(), 682f, rowY, 30f, black, false)
            if (line.discountAmount > 0) {
                val oldRate = rupees(line.originalUnitPrice)
                val oldPaint = textPaint(22f, muted, false).apply { textAlign = Paint.Align.RIGHT }
                val oldWidth = oldPaint.measureText(oldRate)
                canvas.drawText(oldRate, 830f, rowY - 8f, oldPaint)
                canvas.drawLine(830f - oldWidth, rowY - 16f, 830f, rowY - 16f, strokePaint(red, 2.5f))
                drawRight(canvas, rupees(line.unitPrice), 830f, rowY + 27f, 25f, red, true)
            } else {
                drawRight(canvas, rupees(line.unitPrice), 830f, rowY + 8f, 28f, black, false)
            }
            drawRight(canvas, rupees(line.amount), 972f, rowY, 30f, black, true)""",
    "invoice discounted rates")
invoice = once(invoice, "        val thankY = totalTop + 174f",
    """        val savings = bill.totalSavings
        val thankY: Float
        if (savings > 0) {
            canvas.drawRoundRect(RectF(78f, totalTop + 108f, 1002f, totalTop + 172f), 18f, 18f, paint(Color.rgb(220, 245, 228)))
            drawCentered(canvas, "YOU SAVED " + rupees(savings) + " WITH CATEGORY DISCOUNTS!", 540f, totalTop + 150f, 28f, Color.rgb(0, 125, 55), true)
            thankY = totalTop + 238f
        } else {
            thankY = totalTop + 174f
        }""", "invoice savings banner")
INVOICE.write_text(invoice)

gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 2", "versionCode = 3", "app version code")
gradle = once(gradle, 'versionName = "1.1.0"', 'versionName = "1.3.0"', "app version name")
GRADLE.write_text(gradle)

assert "getCategoryDiscounts" in DATA.read_text()
assert "getBillsBetween" in DATA.read_text()
assert "SalesExcelExporter.generate" in MAIN.read_text()
assert "ActivityResultContracts.CreateDocument" in MAIN.read_text()
assert "YOU SAVED " in INVOICE.read_text()
print("v1.3.0 feature sources updated.")
