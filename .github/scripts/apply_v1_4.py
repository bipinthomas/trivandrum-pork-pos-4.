from pathlib import Path

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
DATA = ROOT / "data" / "PosDatabase.kt"
MAIN = ROOT / "MainActivity.kt"
INVOICE = ROOT / "InvoiceImageGenerator.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")

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

# Persist both values in the existing key/value settings table; no destructive
# database migration is needed and existing sales remain untouched.
database = DATA.read_text()
database = once(
    database,
    '    val billPrefix: String = "TP"\n)',
    '    val billPrefix: String = "TP",\n    val fssaiNumber: String = "",\n    val kitchenWhatsAppNumber: String = ""\n)',
    "BusinessSettings fields"
)
database = once(
    database,
    '            billPrefix = values["billPrefix"] ?: "TP"\n        )',
    '            billPrefix = values["billPrefix"] ?: "TP",\n            fssaiNumber = values["fssaiNumber"] ?: "",\n            kitchenWhatsAppNumber = values["kitchenWhatsAppNumber"] ?: ""\n        )',
    "load FSSAI and kitchen WhatsApp settings"
)
database = once(
    database,
    '            "billPrefix" to settings.billPrefix\n        )',
    '            "billPrefix" to settings.billPrefix,\n            "fssaiNumber" to settings.fssaiNumber,\n            "kitchenWhatsAppNumber" to settings.kitchenWhatsAppNumber\n        )',
    "save FSSAI and kitchen WhatsApp settings"
)
DATA.write_text(database)

main = MAIN.read_text()

settings_screen = """@Composable
private fun SettingsScreen(settings: BusinessSettings, onSave: (BusinessSettings) -> Unit) {
    var name by remember(settings) { mutableStateOf(settings.businessName) }
    var contact by remember(settings) { mutableStateOf(settings.contactNumber) }
    var location by remember(settings) { mutableStateOf(settings.location) }
    var tagline by remember(settings) { mutableStateOf(settings.tagline) }
    var prefix by remember(settings) { mutableStateOf(settings.billPrefix) }
    var fssaiNumber by remember(settings) { mutableStateOf(settings.fssaiNumber) }
    var kitchenNumber by remember(settings) { mutableStateOf(settings.kitchenWhatsAppNumber) }
    var formError by remember(settings) { mutableStateOf("") }

    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Business Settings", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(42.dp).clip(CircleShape).background(Yellow), contentAlignment = Alignment.Center) { Icon(Icons.Filled.Storefront, null, tint = Ink) }
                    Spacer(Modifier.width(10.dp)); Text("Invoice & Store Identity", fontSize = 17.sp, fontWeight = FontWeight.Bold)
                }
                FormLabel("Business Name")
                OutlinedTextField(name, { name = it }, Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp))
                FormLabel("Contact Number")
                OutlinedTextField(contact, { contact = it.filter { c -> c.isDigit() || c == '+' }.take(16) }, Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(12.dp))
                FormLabel("Shop Location")
                OutlinedTextField(location, { location = it }, Modifier.fillMaxWidth(), minLines = 2, shape = RoundedCornerShape(12.dp))
                FormLabel("Invoice Tagline")
                OutlinedTextField(tagline, { tagline = it }, Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp))
                FormLabel("Bill Number Prefix")
                OutlinedTextField(prefix, { prefix = it.uppercase(Locale.ENGLISH).filter { c -> c.isLetterOrDigit() }.take(5) }, Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp))
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Text("FSSAI Details", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                FormLabel("FSSAI Licence / Registration Number")
                OutlinedTextField(
                    value = fssaiNumber,
                    onValueChange = { fssaiNumber = it.filter(Char::isDigit).take(14); formError = "" },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    placeholder = { Text("Enter 14-digit FSSAI number") }
                )
                Text("This number will be printed on the customer invoice when provided.", color = Muted, fontSize = 12.sp, lineHeight = 18.sp)
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Chat, null, tint = Green, modifier = Modifier.size(24.dp))
                    Spacer(Modifier.width(8.dp))
                    Text("Kitchen WhatsApp", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                }
                FormLabel("Kitchen WhatsApp Number")
                OutlinedTextField(
                    value = kitchenNumber,
                    onValueChange = { kitchenNumber = it.filter { c -> c.isDigit() || c == '+' }.take(16); formError = "" },
                    modifier = Modifier.fillMaxWidth(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    placeholder = { Text("e.g. 9876543210") }
                )
                Text("Optional. A 10-digit Indian mobile number is automatically routed with country code +91. After the customer invoice opens, the app will ask you to send a separate kitchen image containing only the customer name and item quantities.", color = Muted, fontSize = 12.sp, lineHeight = 18.sp)
                Text("WhatsApp requires a final Send tap; the app cannot silently send messages.", color = Muted, fontSize = 11.sp, lineHeight = 16.sp)
            }
        }
        if (formError.isNotBlank()) Text(formError, color = Red, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        Button(onClick = {
            when {
                fssaiNumber.isNotBlank() && fssaiNumber.length != 14 -> formError = "Enter all 14 digits of the FSSAI number, or leave it blank."
                kitchenNumber.isNotBlank() && normalizeWhatsAppNumber(kitchenNumber).isBlank() -> formError = "Enter a valid kitchen WhatsApp number with 10 to 15 digits."
                else -> onSave(BusinessSettings(
                    businessName = name.trim(),
                    contactNumber = contact.trim(),
                    location = location.trim(),
                    tagline = tagline.trim(),
                    billPrefix = prefix.ifBlank { "TP" },
                    fssaiNumber = fssaiNumber.trim(),
                    kitchenWhatsAppNumber = kitchenNumber.trim()
                ))
            }
        }, modifier = Modifier.fillMaxWidth().height(56.dp), colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink), shape = RoundedCornerShape(14.dp)) {
            Icon(Icons.Filled.Check, null); Spacer(Modifier.width(8.dp)); Text("Save Settings", fontWeight = FontWeight.ExtraBold)
        }
        Spacer(Modifier.height(20.dp))
    }
}

"""
main = between(main, "@Composable\nprivate fun SettingsScreen(", "\nprivate fun shareInvoiceImage", settings_screen, "FSSAI and kitchen settings screen")

main = once(
    main,
    "    var deleteCandidate by remember { mutableStateOf<Product?>(null) }\n",
    "    var deleteCandidate by remember { mutableStateOf<Product?>(null) }\n    var pendingKitchenBill by remember { mutableStateOf<Bill?>(null) }\n",
    "pending kitchen order state"
)

main = once(
    main,
    """    fun shareBill(bill: Bill) {
        try {
            val imageFile = InvoiceImageGenerator(context).generate(bill, settings)
            shareInvoiceImage(context, imageFile, bill, settings)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create invoice image: ${e.localizedMessage ?: "Unknown error"}", Toast.LENGTH_LONG).show()
        }
    }
""",
    """    fun shareBill(bill: Bill) {
        try {
            val imageFile = InvoiceImageGenerator(context).generate(bill, settings)
            shareInvoiceImage(context, imageFile, bill, settings)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create invoice image: ${e.localizedMessage ?: "Unknown error"}", Toast.LENGTH_LONG).show()
        }
    }

    fun shareKitchenOrder(bill: Bill) {
        try {
            val imageFile = KitchenOrderImageGenerator(context).generate(bill)
            shareKitchenOrderImage(context, imageFile, settings.kitchenWhatsAppNumber)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create kitchen order image: ${e.localizedMessage ?: "Unknown error"}", Toast.LENGTH_LONG).show()
        }
    }
""",
    "kitchen share callback"
)

main = once(
    main,
    "                                    shareBill(newBill)\n",
    "                                    if (settings.kitchenWhatsAppNumber.isNotBlank()) pendingKitchenBill = newBill\n                                    shareBill(newBill)\n",
    "queue kitchen order after customer invoice"
)

main = once(
    main,
    """    deleteCandidate?.let { product ->
        AlertDialog(
            onDismissRequest = { deleteCandidate = null },
            title = { Text("Delete menu item?") },
            text = { Text("${product.name} will be removed from the menu. Existing bills will remain unchanged.") },
            confirmButton = {
                TextButton(onClick = { db.deleteProduct(product.id); deleteCandidate = null; refresh() }) { Text("Delete", color = Red) }
            },
            dismissButton = { TextButton(onClick = { deleteCandidate = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun MainHeader""",
    """    deleteCandidate?.let { product ->
        AlertDialog(
            onDismissRequest = { deleteCandidate = null },
            title = { Text("Delete menu item?") },
            text = { Text("${product.name} will be removed from the menu. Existing bills will remain unchanged.") },
            confirmButton = {
                TextButton(onClick = { db.deleteProduct(product.id); deleteCandidate = null; refresh() }) { Text("Delete", color = Red) }
            },
            dismissButton = { TextButton(onClick = { deleteCandidate = null }) { Text("Cancel") } }
        )
    }

    pendingKitchenBill?.let { kitchenBill ->
        AlertDialog(
            onDismissRequest = { pendingKitchenBill = null },
            title = { Text("Send order to kitchen?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(kitchenBill.customerName, fontWeight = FontWeight.Bold)
                    Text("A separate image with only the customer name, item names and quantities will be opened for the saved kitchen WhatsApp number.", color = Muted, fontSize = 13.sp, lineHeight = 19.sp)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    pendingKitchenBill = null
                    shareKitchenOrder(kitchenBill)
                }) { Text("Send to Kitchen", color = Green, fontWeight = FontWeight.Bold) }
            },
            dismissButton = {
                TextButton(onClick = { pendingKitchenBill = null }) { Text("Skip") }
            }
        )
    }
}

@Composable
private fun MainHeader""",
    "kitchen order send prompt"
)

main = once(
    main,
    "\nprivate fun isPackageInstalled",
    """
private fun normalizeWhatsAppNumber(raw: String): String {
    val digits = raw.filter(Char::isDigit)
    return when {
        digits.length == 10 -> "91$digits"
        digits.length == 11 && digits.startsWith("0") -> "91${digits.drop(1)}"
        digits.length in 11..15 -> digits
        else -> ""
    }
}

private fun shareKitchenOrderImage(context: Context, imageFile: File, rawNumber: String) {
    val recipientNumber = normalizeWhatsAppNumber(rawNumber)
    if (recipientNumber.isBlank()) {
        Toast.makeText(context, "Kitchen WhatsApp number is invalid. Check Settings.", Toast.LENGTH_LONG).show()
        return
    }
    val uri: Uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", imageFile)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/png"
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra("jid", "${recipientNumber}@s.whatsapp.net")
        clipData = ClipData.newUri(context.contentResolver, "Kitchen order", uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    val whatsappBusiness = "com.whatsapp.w4b"
    val whatsapp = "com.whatsapp"
    val installedPackage = when {
        isPackageInstalled(context, whatsappBusiness) -> whatsappBusiness
        isPackageInstalled(context, whatsapp) -> whatsapp
        else -> null
    }
    if (installedPackage != null) {
        intent.setPackage(installedPackage)
        context.startActivity(intent)
    } else {
        context.startActivity(Intent.createChooser(intent, "Send kitchen order"))
    }
}

private fun isPackageInstalled""",
    "kitchen WhatsApp image handoff"
)
MAIN.write_text(main)

invoice = INVOICE.read_text()
invoice = once(
    invoice,
    "        val footerTop = height - 170f",
    """        if (settings.fssaiNumber.isNotBlank()) {
            drawCenteredFitted(
                canvas,
                "FSSAI Lic. No.: ${settings.fssaiNumber}",
                540f,
                thankY + 55f,
                920f,
                26f,
                muted,
                true
            )
        }

        val footerTop = height - 170f""",
    "print FSSAI number on invoice"
)
INVOICE.write_text(invoice)

kitchen_generator = r'''package com.trivandrumpork.pos

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import com.trivandrumpork.pos.data.Bill
import java.io.File
import java.io.FileOutputStream
import java.util.Locale

/**
 * Creates a deliberately minimal kitchen ticket.
 * The image contains only the kitchen heading, customer name, product names and counts.
 */
class KitchenOrderImageGenerator(private val context: Context) {
    fun generate(bill: Bill): File {
        val width = 1080
        val height = 430 + (bill.items.size.coerceAtLeast(1) * 110)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)

        val navy = Color.rgb(23, 27, 37)
        val yellow = Color.rgb(255, 201, 20)
        val background = Color.rgb(244, 246, 249)
        val black = Color.rgb(24, 27, 31)
        val muted = Color.rgb(105, 111, 120)
        val line = Color.rgb(225, 228, 233)
        val white = Color.WHITE

        canvas.drawColor(background)
        canvas.drawRoundRect(RectF(48f, 48f, 1032f, height - 48f), 34f, 34f, paint(white))
        canvas.drawRoundRect(RectF(48f, 48f, 1032f, 190f), 34f, 34f, paint(navy))
        canvas.drawRect(RectF(48f, 154f, 1032f, 190f), paint(navy))
        drawCentered(canvas, "KITCHEN ORDER", 540f, 137f, 48f, yellow, true)

        canvas.drawText("CUSTOMER", 112f, 242f, textPaint(25f, muted, true))
        drawFitted(canvas, bill.customerName, 112f, 292f, 850f, 43f, black, true)
        canvas.drawLine(90f, 326f, 990f, 326f, strokePaint(line, 3f))

        var rowY = 382f
        bill.items.forEachIndexed { index, item ->
            drawFitted(canvas, item.productName, 112f, rowY, 700f, 36f, black, true)
            drawRight(canvas, "× ${item.quantity}", 956f, rowY, 40f, navy, true)
            if (index < bill.items.lastIndex) {
                canvas.drawLine(112f, rowY + 36f, 968f, rowY + 36f, strokePaint(line, 2f))
            }
            rowY += 110f
        }

        val folder = File(context.cacheDir, "kitchen-orders").apply { mkdirs() }
        val output = File(folder, "${bill.billNo}_kitchen.png")
        FileOutputStream(output).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
        return output
    }

    private fun paint(color: Int) = Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color }

    private fun strokePaint(color: Int, width: Float) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = color
        style = Paint.Style.STROKE
        strokeWidth = width
    }

    private fun textPaint(size: Float, color: Int, bold: Boolean) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size
        this.color = color
        typeface = Typeface.create("sans-serif", if (bold) Typeface.BOLD else Typeface.NORMAL)
    }

    private fun drawCentered(canvas: Canvas, text: String, x: Float, y: Float, size: Float, color: Int, bold: Boolean) {
        val p = textPaint(size, color, bold)
        p.textAlign = Paint.Align.CENTER
        canvas.drawText(text, x, y, p)
    }

    private fun drawRight(canvas: Canvas, text: String, x: Float, y: Float, size: Float, color: Int, bold: Boolean) {
        val p = textPaint(size, color, bold)
        p.textAlign = Paint.Align.RIGHT
        canvas.drawText(text, x, y, p)
    }

    private fun drawFitted(
        canvas: Canvas, text: String, x: Float, baseline: Float, maxWidth: Float,
        size: Float, color: Int, bold: Boolean
    ) {
        var currentSize = size
        var p = textPaint(currentSize, color, bold)
        while (p.measureText(text) > maxWidth && currentSize > 18f) {
            currentSize -= 1f
            p = textPaint(currentSize, color, bold)
        }
        var fitted = text
        while (p.measureText(fitted) > maxWidth && fitted.length > 2) {
            fitted = fitted.dropLast(2).trimEnd() + "…"
        }
        canvas.drawText(fitted, x, baseline, p)
    }
}
'''
(ROOT / "KitchenOrderImageGenerator.kt").write_text(kitchen_generator)

gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 3", "versionCode = 4", "Android version code")
gradle = once(gradle, 'versionName = "1.3.0"', 'versionName = "1.4.0"', "Android version name")
GRADLE.write_text(gradle)

assert "fssaiNumber" in DATA.read_text()
assert "kitchenWhatsAppNumber" in DATA.read_text()
assert "KitchenOrderImageGenerator" in MAIN.read_text()
assert 'putExtra("jid"' in MAIN.read_text()
assert "FSSAI Lic. No." in INVOICE.read_text()
assert 'versionName = "1.4.0"' in GRADLE.read_text()
print("v1.4.0 FSSAI and kitchen WhatsApp sources updated.")
