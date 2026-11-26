from pathlib import Path
import re

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
MAIN = ROOT / "MainActivity.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")
MANIFEST = Path("TrivandrumPorkPOS-Android/app/src/main/AndroidManifest.xml")

def once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)

main = MAIN.read_text()

# Defer customer sharing until the cashier chooses a reliable route.
main = once(
    main,
    "    var pendingKitchenBill by remember { mutableStateOf<Bill?>(null) }\n",
    "    var pendingKitchenBill by remember { mutableStateOf<Bill?>(null) }\n"
    "    var pendingBillShare by remember { mutableStateOf<Bill?>(null) }\n"
    "    var pendingKitchenAfterBillShare by remember { mutableStateOf<Bill?>(null) }\n",
    "customer bill share state"
)

start = main.find("    fun shareBill(bill: Bill) {")
end = main.find("    fun shareKitchenOrder(bill: Bill) {", start)
if start < 0 or end < 0 or end <= start:
    raise SystemExit("Could not locate the customer bill sharing callback.")
share_callbacks = """    fun shareBill(bill: Bill) {
        pendingBillShare = bill
    }

    fun shareBillImage(bill: Bill) {
        try {
            val imageFile = InvoiceImageGenerator(context).generate(bill, settings)
            shareInvoiceImage(context, imageFile, bill, settings)
        } catch (e: Exception) {
            Toast.makeText(
                context,
                "Could not create invoice image: " + (e.localizedMessage ?: "Unknown error"),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    fun finishBillShare() {
        pendingBillShare = null
        pendingKitchenAfterBillShare?.let { pendingKitchenBill = it }
        pendingKitchenAfterBillShare = null
    }

"""
main = main[:start] + share_callbacks + main[end:]

# Avoid showing the kitchen confirmation on top of the customer-share choice.
main = once(
    main,
    "                                    if (settings.kitchenWhatsAppNumber.isNotBlank()) pendingKitchenBill = newBill\n",
    "                                    if (settings.kitchenWhatsAppNumber.isNotBlank()) pendingKitchenAfterBillShare = newBill\n",
    "queue kitchen after customer-share choice"
)

# Add the choice dialog before the existing kitchen prompt.
marker = "    pendingKitchenBill?.let { kitchenBill ->"
dialog = """    pendingBillShare?.let { customerBill ->
        AlertDialog(
            onDismissRequest = { finishBillShare() },
            title = { Text("Send bill to " + customerBill.customerName + "?") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("Send bill details opens the exact WhatsApp chat using the phone number on the bill. It works even when the number is new and not saved in Contacts.")
                    Text("Share invoice image attaches the bill PNG. WhatsApp may show its recipient picker when there is no previous chat with that number.", color = Muted, fontSize = 12.sp, lineHeight = 18.sp)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    finishBillShare()
                    sendBillDetailsToWhatsApp(context, customerBill, settings)
                }) {
                    Text("Send Bill Details", color = Green, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                Row {
                    TextButton(onClick = {
                        finishBillShare()
                        shareBillImage(customerBill)
                    }) { Text("Share Image") }
                    TextButton(onClick = { finishBillShare() }) { Text("Cancel") }
                }
            }
        )
    }

"""
main = once(main, marker, dialog + marker, "customer WhatsApp route selection dialog")

old_normalizer = """private fun normalizeWhatsAppNumber(raw: String): String {
    val digits = raw.filter(Char::isDigit)
    return when {
        digits.length == 10 -> "91$digits"
        digits.length == 11 && digits.startsWith("0") -> "91${digits.drop(1)}"
        digits.length in 11..15 -> digits
        else -> ""
    }
}"""
new_normalizer = """private fun normalizeWhatsAppNumber(raw: String): String {
    val entered = raw.filter(Char::isDigit)
    val digits = if (entered.startsWith("00")) entered.drop(2) else entered
    return when {
        digits.length == 10 -> "91" + digits
        digits.length == 11 && digits.startsWith("0") -> "91" + digits.drop(1)
        digits.length in 11..15 -> digits
        else -> ""
    }
}"""
main = once(main, old_normalizer, new_normalizer, "normalize WhatsApp recipient number")
MAIN.write_text(main)

# Keep WhatsApp Business and WhatsApp visible to PackageManager on Android 11+.
manifest = MANIFEST.read_text()
if "<queries>" not in manifest:
    queries = """    <queries>
        <package android:name="com.whatsapp" />
        <package android:name="com.whatsapp.w4b" />
    </queries>
"""
    if "<application" not in manifest:
        raise SystemExit("Android manifest has no application element.")
    manifest = manifest.replace("<application", queries + "    <application", 1)
if 'android:name="com.whatsapp"' not in manifest or 'android:name="com.whatsapp.w4b"' not in manifest:
    raise SystemExit("WhatsApp package visibility declarations are incomplete.")
MANIFEST.write_text(manifest)

# Extend number normalization and add the official Click to Chat text-bill route.
anchor = "\nprivate fun shareKitchenOrderImage("
if anchor not in main:
    raise SystemExit("Could not find WhatsApp helper insertion point.")

new_helpers = r'''
private fun buildWhatsAppBillMessage(bill: Bill, settings: BusinessSettings): String {
    return buildString {
        append("Thank you for ordering from ")
        append(settings.businessName)
        appendLine("!")
        append("Customer: ")
        appendLine(bill.customerName)
        append("Bill No.: ")
        appendLine(bill.billNo)
        append("Date: ")
        appendLine(formatDate(bill.createdAt))
        appendLine()
        appendLine("ITEMS")
        bill.items.forEach { item ->
            append(item.productName)
            append(" x ")
            append(item.quantity)
            append(" = ")
            appendLine(rupees(item.amount))
        }
        if (bill.totalSavings > 0) {
            append("You saved: ")
            appendLine(rupees(bill.totalSavings))
        }
        appendLine()
        append("TOTAL: ")
        appendLine(rupees(bill.total))
        if (bill.loyaltyPointsEarned > 0) {
            append("Loyalty points earned: ")
            appendLine(bill.loyaltyPointsEarned)
            append("Loyalty points balance: ")
            appendLine(bill.loyaltyPointsBalance)
        }
        appendLine()
        append(settings.location)
    }
}

/** Uses WhatsApp's documented Click to Chat link, which does not require a saved contact. */
private fun sendBillDetailsToWhatsApp(context: Context, bill: Bill, settings: BusinessSettings) {
    val recipientNumber = normalizeWhatsAppNumber(bill.mobile)
    if (recipientNumber.isBlank()) {
        Toast.makeText(
            context,
            "Customer mobile number is invalid. Enter 10 digits or an international number.",
            Toast.LENGTH_LONG
        ).show()
        return
    }

    val message = buildWhatsAppBillMessage(bill, settings)
    val link = Uri.parse("https://wa.me/" + recipientNumber + "?text=" + Uri.encode(message))
    val knownWhatsAppPackages = listOf("com.whatsapp.w4b", "com.whatsapp")
    var opened = false

    for (packageName in knownWhatsAppPackages) {
        if (isPackageInstalled(context, packageName)) {
            try {
                context.startActivity(Intent(Intent.ACTION_VIEW, link).apply {
                    setPackage(packageName)
                })
                opened = true
                break
            } catch (_: Exception) {
                // Try the other WhatsApp app, then the verified web link below.
            }
        }
    }

    if (!opened) {
        try {
            context.startActivity(Intent(Intent.ACTION_VIEW, link))
            opened = true
        } catch (e: Exception) {
            Toast.makeText(
                context,
                "Could not open WhatsApp chat: " + (e.localizedMessage ?: "Unknown error"),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    if (opened) {
        Toast.makeText(
            context,
            "Bill details are ready in the customer's WhatsApp chat. Tap Send in WhatsApp.",
            Toast.LENGTH_LONG
        ).show()
    }
}
'''
main = main.replace(anchor, "\n" + new_helpers + anchor, 1)
MAIN.write_text(main)

# Bump the patch release without changing the database schema or app data.
gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 7", "versionCode = 8", "Android version code")
gradle = once(gradle, 'versionName = "1.7.0"', 'versionName = "1.7.1"', "Android version name")
GRADLE.write_text(gradle)

# Assertions prevent a partial WhatsApp change from reaching the release build.
source = MAIN.read_text()
assert "Send Bill Details" in source
assert "sendBillDetailsToWhatsApp(context, customerBill, settings)" in source
assert "https://wa.me/" in source
assert "buildWhatsAppBillMessage" in source
assert "pendingKitchenAfterBillShare" in source
assert 'android:name="com.whatsapp"' in MANIFEST.read_text()
assert 'android:name="com.whatsapp.w4b"' in MANIFEST.read_text()
assert 'versionName = "1.7.1"' in GRADLE.read_text()
print("v1.7.1 unsaved-number WhatsApp Click-to-Chat and recipient visibility fixes applied.")
