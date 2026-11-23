from pathlib import Path
import base64

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
DATA = ROOT / "data" / "PosDatabase.kt"
MAIN = ROOT / "MainActivity.kt"
INVOICE = ROOT / "InvoiceImageGenerator.kt"
EXPORTER = ROOT / "SalesExcelExporter.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")

def once(s, old, new, label):
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 match, found {n}")
    return s.replace(old, new, 1)

parts = sorted(Path(".github/branding").glob("logo-*.b64"))
if not parts:
    raise SystemExit("Missing bill header logo source.")
logo_b64 = "".join(p.read_text().strip() for p in parts)
logo_bytes = base64.b64decode(logo_b64, validate=True)
if len(logo_bytes) < 10000:
    raise SystemExit("Bill header logo is unexpectedly small.")
asset_dir = Path("TrivandrumPorkPOS-Android/app/src/main/assets")
asset_dir.mkdir(parents=True, exist_ok=True)
(asset_dir / "trivandrum_pork_logo.png").write_bytes(logo_bytes)

db = DATA.read_text()
db = once(db, "    val items: List<BillLine>\n) {",
    """    val items: List<BillLine>,
    val loyaltyPointsEarned: Int = 0,
    val loyaltyPointsBalance: Int = 0,
    val loyaltyRewardUnlocked: Boolean = false
) {""", "Bill loyalty fields")
db = once(db, "class PosDatabase(context: Context)",
    """data class LoyaltyAccount(
    val mobile: String,
    val customerName: String,
    val currentPoints: Int,
    val totalEarned: Int,
    val totalRedeemed: Int
)

private fun loyaltyMobileKey(raw: String): String {
    val digits = raw.filter(Char::isDigit)
    return when {
        digits.length == 10 -> digits
        digits.length == 11 && digits.startsWith("0") -> digits.drop(1)
        digits.length == 12 && digits.startsWith("91") -> digits.drop(2)
        else -> ""
    }
}

class PosDatabase(context: Context)""", "loyalty account model")
db = once(db, "            created_at INTEGER NOT NULL\n        )\"\"\".trimIndent())",
    """            created_at INTEGER NOT NULL,
            loyalty_points_earned INTEGER NOT NULL DEFAULT 0,
            loyalty_points_balance INTEGER NOT NULL DEFAULT 0,
            loyalty_reward_unlocked INTEGER NOT NULL DEFAULT 0
        )\"\"\".trimIndent())""", "new bill loyalty columns")
db = once(db, '        db.execSQL("CREATE TABLE settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")',
    """        db.execSQL("CREATE TABLE settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")
        createLoyaltyTables(db)""", "create loyalty tables on fresh install")
db = once(db,
    "            db.execSQL(\"INSERT OR IGNORE INTO categories(name) VALUES('Other')\")\n        }\n    }\n\n    private fun seedProducts",
    """            db.execSQL("INSERT OR IGNORE INTO categories(name) VALUES('Other')")
        }
        if (oldVersion < 3) {
            db.execSQL("ALTER TABLE bills ADD COLUMN loyalty_points_earned INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bills ADD COLUMN loyalty_points_balance INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bills ADD COLUMN loyalty_reward_unlocked INTEGER NOT NULL DEFAULT 0")
            createLoyaltyTables(db)
        }
    }

    private fun seedProducts""", "database migration to loyalty")
db = once(db, "    private fun seedProducts(db: SQLiteDatabase) {",
    """    private fun createLoyaltyTables(db: SQLiteDatabase) {
        db.execSQL(\"\"\"CREATE TABLE IF NOT EXISTS customer_loyalty (
            mobile TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            current_points INTEGER NOT NULL DEFAULT 0,
            total_earned INTEGER NOT NULL DEFAULT 0,
            total_redeemed INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL
        )\"\"\")
        db.execSQL(\"\"\"CREATE TABLE IF NOT EXISTS loyalty_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mobile TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            bill_id INTEGER,
            points_change INTEGER NOT NULL,
            description TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )\"\"\")
    }

    private fun seedProducts(db: SQLiteDatabase) {""", "loyalty tables helper")
db = once(db, "private const val DB_VERSION = 2", "private const val DB_VERSION = 3", "database version")
db = once(db, "            val total = lines.sumOf { it.amount }\n            val values = ContentValues().apply {",
    """            val total = lines.sumOf { it.amount }
            val mobileKey = loyaltyMobileKey(mobile)
            val earnedPoints = if (mobileKey.isNotBlank()) (total / 100) * 5 else 0
            val prior = if (mobileKey.isBlank()) null else db.query(
                "customer_loyalty", arrayOf("current_points", "total_earned", "total_redeemed"),
                "mobile=?", arrayOf(mobileKey), null, null, null
            ).use { c ->
                if (c.moveToFirst()) Triple(c.getInt(0), c.getInt(1), c.getInt(2)) else null
            }
            val previousPoints = prior?.first ?: 0
            val pointsBalance = previousPoints + earnedPoints
            val rewardUnlocked = previousPoints < 200 && pointsBalance >= 200
            val values = ContentValues().apply {""", "calculate points")
db = once(db, '                put("total", total); put("created_at", System.currentTimeMillis())',
    """                put("total", total); put("created_at", System.currentTimeMillis())
                put("loyalty_points_earned", earnedPoints)
                put("loyalty_points_balance", pointsBalance)
                put("loyalty_reward_unlocked", if (rewardUnlocked) 1 else 0)""", "save points with bill")
db = once(db, "            db.setTransactionSuccessful()\n            return billId",
    """            if (mobileKey.isNotBlank() && earnedPoints > 0) {
                val accountValues = ContentValues().apply {
                    put("mobile", mobileKey)
                    put("customer_name", customerName.trim())
                    put("current_points", pointsBalance)
                    put("total_earned", (prior?.second ?: 0) + earnedPoints)
                    put("total_redeemed", prior?.third ?: 0)
                    put("updated_at", System.currentTimeMillis())
                }
                db.insertWithOnConflict("customer_loyalty", null, accountValues, SQLiteDatabase.CONFLICT_REPLACE)
                val transaction = ContentValues().apply {
                    put("mobile", mobileKey); put("customer_name", customerName.trim())
                    put("bill_id", billId); put("points_change", earnedPoints)
                    put("description", "Purchase points - " + billNo)
                    put("created_at", System.currentTimeMillis())
                }
                db.insertOrThrow("loyalty_transactions", null, transaction)
            }
            db.setTransactionSuccessful()
            return billId""", "persist loyalty award")
db = db.replace(
    "                    items = getBillLines(id)\n                )",
    """                    items = getBillLines(id),
                    loyaltyPointsEarned = c.getInt(c.getColumnIndexOrThrow("loyalty_points_earned")),
                    loyaltyPointsBalance = c.getInt(c.getColumnIndexOrThrow("loyalty_points_balance")),
                    loyaltyRewardUnlocked = c.getInt(c.getColumnIndexOrThrow("loyalty_reward_unlocked")) == 1
                )"""
)
db = db.replace(
    "                items = emptyList()\n            )",
    """                items = emptyList(),
                loyaltyPointsEarned = c.getInt(c.getColumnIndexOrThrow("loyalty_points_earned")),
                loyaltyPointsBalance = c.getInt(c.getColumnIndexOrThrow("loyalty_points_balance")),
                loyaltyRewardUnlocked = c.getInt(c.getColumnIndexOrThrow("loyalty_reward_unlocked")) == 1
            )"""
)
if "loyaltyPointsEarned = c.getInt" not in db or "loyaltyPointsBalance = c.getInt" not in db:
    raise SystemExit("Could not wire loyalty fields into bill reads.")
db = once(db, "    fun getSales(fromMillis: Long): Pair<Int, Int> {",
    """    fun getLoyaltyAccount(rawMobile: String): LoyaltyAccount? {
        val mobile = loyaltyMobileKey(rawMobile)
        if (mobile.isBlank()) return null
        return readableDatabase.query(
            "customer_loyalty", null, "mobile=?", arrayOf(mobile), null, null, null
        ).use { c ->
            if (!c.moveToFirst()) null else LoyaltyAccount(
                mobile = c.getString(c.getColumnIndexOrThrow("mobile")),
                customerName = c.getString(c.getColumnIndexOrThrow("customer_name")),
                currentPoints = c.getInt(c.getColumnIndexOrThrow("current_points")),
                totalEarned = c.getInt(c.getColumnIndexOrThrow("total_earned")),
                totalRedeemed = c.getInt(c.getColumnIndexOrThrow("total_redeemed"))
            )
        }
    }

    fun redeemLoyaltyPoints(rawMobile: String): Boolean {
        val mobile = loyaltyMobileKey(rawMobile)
        if (mobile.isBlank()) return false
        val db = writableDatabase
        db.beginTransaction()
        try {
            val account = db.query("customer_loyalty", null, "mobile=?", arrayOf(mobile), null, null, null).use { c ->
                if (!c.moveToFirst() || c.getInt(c.getColumnIndexOrThrow("current_points")) < 200) null
                else Triple(
                    c.getString(c.getColumnIndexOrThrow("customer_name")),
                    c.getInt(c.getColumnIndexOrThrow("current_points")),
                    c.getInt(c.getColumnIndexOrThrow("total_redeemed"))
                )
            } ?: return false
            val now = System.currentTimeMillis()
            db.update("customer_loyalty", ContentValues().apply {
                put("current_points", account.second - 200)
                put("total_redeemed", account.third + 200)
                put("updated_at", now)
            }, "mobile=?", arrayOf(mobile))
            db.insertOrThrow("loyalty_transactions", null, ContentValues().apply {
                put("mobile", mobile); put("customer_name", account.first)
                put("points_change", -200); put("description", "200-point reward redeemed at counter")
                put("created_at", now)
            })
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }

    fun getSales(fromMillis: Long): Pair<Int, Int> {""", "loyalty lookup and redemption APIs")
DATA.write_text(db)

invoice = INVOICE.read_text()
if "import android.graphics.BitmapFactory" not in invoice:
    invoice = once(invoice, "import android.graphics.Bitmap\n",
        "import android.graphics.Bitmap\nimport android.graphics.BitmapFactory\n", "logo import")
start = invoice.find("        // Brand header")
end = invoice.find("        // Invoice title", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate the original invoice header block.")
logo_block = """        // Customer-provided Trivandrum Pork logo replaces the illustrated header.
        val logoRect = RectF(54f, 24f, 1026f, 365f)
        canvas.drawRect(logoRect, paint(white))
        val logo = context.assets.open("trivandrum_pork_logo.png").use { BitmapFactory.decodeStream(it) }
        if (logo != null) {
            val scale = min(logoRect.width() / logo.width, logoRect.height() / logo.height)
            val drawWidth = logo.width * scale
            val drawHeight = logo.height * scale
            val leftLogo = (width - drawWidth) / 2f
            val topLogo = logoRect.top + (logoRect.height() - drawHeight) / 2f
            canvas.drawBitmap(logo, null, RectF(leftLogo, topLogo, leftLogo + drawWidth, topLogo + drawHeight), paint(white))
            logo.recycle()
        }

"""
invoice = invoice[:start] + logo_block + invoice[end:]
start = invoice.find("        // Invoice title")
end = invoice.find("        canvas.drawLine(78f, 512f", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate invoice title/take-away box.")
metadata = """        canvas.drawText("Bill No  :  " + bill.billNo, 88f, 424f, textPaint(33f, black, false))
        val dateText = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.ENGLISH).format(Date(bill.createdAt))
        canvas.drawText("Date      :  " + dateText, 88f, 476f, textPaint(31f, black, false))
"""
invoice = invoice[:start] + metadata + invoice[end:]
invoice = once(invoice, 'canvas.drawText("Customer  :", 88f, 570f', 'canvas.drawText("Customer  :", 88f, 530f', "customer y")
invoice = once(invoice, 'drawFitted(canvas, bill.customerName, 300f, 570f', 'drawFitted(canvas, bill.customerName, 300f, 530f', "customer name y")
invoice = once(invoice, 'canvas.drawText("Mobile      :", 88f, 620f', 'canvas.drawText("Mobile      :", 88f, 578f', "mobile y")
invoice = once(invoice, 'canvas.drawText(bill.mobile, 300f, 620f', 'canvas.drawText(bill.mobile, 300f, 578f', "mobile text y")
invoice = once(invoice, "canvas.drawLine(78f, 652f, 1002f, 652f", "canvas.drawLine(78f, 612f, 1002f, 612f", "customer separator")
invoice = once(invoice, "val tableTop = 682f", "val tableTop = 642f", "table position")
old_thank = """        val thankY = totalTop + 174f
        canvas.drawText("Thank You!", 112f, thankY, scriptPaint(57f, red))
"""
new_thank = """        val pointsLine = "LOYALTY: +" + bill.loyaltyPointsEarned + " POINTS  |  BALANCE: " + bill.loyaltyPointsBalance + " POINTS"
        drawCenteredFitted(canvas, pointsLine, 540f, totalTop + 135f, 900f, 25f, navy, true)
        if (bill.loyaltyPointsBalance >= 200) {
            drawCenteredFitted(canvas, "200 POINTS UNLOCKED - REDEEM AT COUNTER", 540f, totalTop + 168f, 900f, 25f, Color.rgb(0, 125, 55), true)
        }
        if (bill.totalSavings > 0) {
            drawCenteredFitted(
                canvas,
                "SPECIAL DISCOUNT APPLIED - YOU SAVED " + rupees(bill.totalSavings) + "/-",
                540f,
                totalTop + 202f,
                920f,
                25f,
                Color.rgb(0, 125, 55),
                true
            )
        }
        val thankY = totalTop + 254f
        canvas.drawText("Thank You!", 112f, thankY, scriptPaint(57f, red))
"""
invoice = once(invoice, old_thank, new_thank, "loyalty and special discount receipt lines")
INVOICE.write_text(invoice)

exporter = EXPORTER.read_text()
exporter = once(exporter,
    '        rows += listOf("Net Sales", netSales)\n',
    '        rows += listOf("Net Sales", netSales)\n        rows += listOf("Loyalty Points Earned", bills.sumOf { it.loyaltyPointsEarned })\n',
    "loyalty report summary")
exporter = once(exporter,
    '"Discount Amount", "Net Amount")',
    '"Discount Amount", "Net Amount", "Loyalty Points Earned", "Loyalty Balance After Bill", "Reward Unlocked")',
    "loyalty report headers")
exporter = once(exporter,
    'line.unitPrice, line.originalAmount, line.discountAmount, line.amount)',
    'line.unitPrice, line.originalAmount, line.discountAmount, line.amount, bill.loyaltyPointsEarned,\n                    bill.loyaltyPointsBalance, if (bill.loyaltyRewardUnlocked) "Yes" else "No")',
    "loyalty report values")
exporter = once(exporter,
    'val widths = listOf(18, 24, 24, 18, 18, 28, 10, 15, 12, 17, 18, 18, 18)',
    'val widths = listOf(18, 24, 24, 18, 18, 28, 10, 15, 12, 17, 18, 18, 18, 18, 20, 16)',
    "loyalty report widths")
exporter = once(exporter,
    'append("<autoFilter ref=\\"A13:M" + rows.size + "\\"/>")',
    'append("<autoFilter ref=\\"A13:P" + rows.size + "\\"/>")',
    "loyalty report filter range")
EXPORTER.write_text(exporter)

main = MAIN.read_text()
main = once(main, "import androidx.compose.material.icons.filled.Settings\n",
    "import androidx.compose.material.icons.filled.Settings\nimport androidx.compose.material.icons.filled.Star\n",
    "loyalty icon import")
if "import com.trivandrumpork.pos.data.LoyaltyAccount" not in main:
    marker = "import com.trivandrumpork.pos.data."
    pos = main.find(marker)
    if pos < 0:
        raise SystemExit("Could not locate POS data imports.")
    main = main[:pos] + "import com.trivandrumpork.pos.data.LoyaltyAccount\n" + main[pos:]
main = once(main, "private enum class AppScreen { POS, BILLS, MENU, SALES, SETTINGS, ADD_ITEM, BILL_DETAIL }",
    "private enum class AppScreen { POS, BILLS, MENU, SALES, LOYALTY, SETTINGS, ADD_ITEM, BILL_DETAIL }",
    "loyalty screen enum")
main = once(main,
    '        Triple(AppScreen.SALES, "Sales", Icons.Filled.BarChart),',
    '        Triple(AppScreen.SALES, "Sales", Icons.Filled.BarChart),\n        Triple(AppScreen.LOYALTY, "Loyalty", Icons.Filled.Star),',
    "loyalty navigation tab")
main = once(main,
    "                    AppScreen.SALES -> SalesScreen(db = db, bills = bills, onExport = ::exportSalesReport)",
    "                    AppScreen.SALES -> SalesScreen(db = db, bills = bills, onExport = ::exportSalesReport)\n                    AppScreen.LOYALTY -> LoyaltyScreen(db = db)",
    "loyalty screen route")
old_bill = '                                    shareBill(newBill)\n                                    Toast.makeText(context, "' + "$" + '{newBill.billNo} saved successfully", Toast.LENGTH_SHORT).show()'
new_bill = """                                    shareBill(newBill)
                                    if (newBill.loyaltyRewardUnlocked) {
                                        Toast.makeText(context, newBill.customerName + " reached 200 loyalty points. They can redeem at the counter!", Toast.LENGTH_LONG).show()
                                    } else if (newBill.loyaltyPointsEarned > 0) {
                                        Toast.makeText(context, newBill.loyaltyPointsEarned.toString() + " loyalty points added. Balance: " + newBill.loyaltyPointsBalance, Toast.LENGTH_SHORT).show()
                                    }
                                    Toast.makeText(context, newBill.billNo + " saved successfully", Toast.LENGTH_SHORT).show()"""
main = once(main, old_bill, new_bill, "loyalty checkout notification")
old_message = 'putExtra(Intent.EXTRA_TEXT, "Thank you for ordering from ' + "$" + '{settings.businessName}!\\\\nBill: ' + "$" + '{bill.billNo}\\\\nTotal: ' + "$" + '{rupees(bill.total)}")'
new_message = """putExtra(
            Intent.EXTRA_TEXT,
            "Thank you for ordering from " + settings.businessName + "!\\\\nBill: " + bill.billNo + "\\\\nTotal: " + rupees(bill.total) +
                "\\\\nLoyalty points earned: " + bill.loyaltyPointsEarned +
                "\\\\nYour loyalty balance: " + bill.loyaltyPointsBalance +
                if (bill.loyaltyPointsBalance >= 200) "\\\\nYou have unlocked 200 points. Redeem at the counter!" else ""
        )"""
main = once(main, old_message, new_message, "customer WhatsApp loyalty notification")

loyalty_ui = """@Composable
private fun LoyaltyScreen(db: PosDatabase) {
    val context = LocalContext.current
    var mobile by remember { mutableStateOf("") }
    var account by remember { mutableStateOf<LoyaltyAccount?>(null) }
    var searched by remember { mutableStateOf(false) }

    Column(
        Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Customer Loyalty", fontSize = 23.sp, fontWeight = FontWeight.ExtraBold)
        Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
            Column(Modifier.fillMaxWidth().padding(15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Find customer points", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                OutlinedTextField(
                    value = mobile,
                    onValueChange = { mobile = it.filter { c -> c.isDigit() || c == '+' }.take(15); searched = false },
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Customer mobile number") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp)
                )
                Button(
                    onClick = { account = db.getLoyaltyAccount(mobile); searched = true },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink)
                ) { Text("Check Points", fontWeight = FontWeight.Bold) }
            }
        }
        if (searched && account == null) Text("No loyalty record found for this mobile number yet.", color = Muted)
        account?.let { customer ->
            Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White)) {
                Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text(customer.customerName, fontWeight = FontWeight.ExtraBold, fontSize = 20.sp)
                    Text(customer.mobile, color = Muted)
                    Text("AVAILABLE POINTS", fontWeight = FontWeight.Bold, color = Muted, fontSize = 12.sp)
                    Text(customer.currentPoints.toString(), color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 42.sp)
                    Text("Total earned: " + customer.totalEarned + "   •   Redeemed: " + customer.totalRedeemed, color = Muted, fontSize = 12.sp)
                    Text(
                        if (customer.currentPoints >= 200) "Reward unlocked. Redeem 200 points at the counter."
                        else (200 - customer.currentPoints).toString() + " more points to unlock the 200-point reward.",
                        color = if (customer.currentPoints >= 200) Green else Muted,
                        fontWeight = FontWeight.SemiBold
                    )
                    Button(
                        onClick = {
                            if (db.redeemLoyaltyPoints(customer.mobile)) {
                                account = db.getLoyaltyAccount(customer.mobile)
                                Toast.makeText(context, "200 loyalty points redeemed at counter.", Toast.LENGTH_LONG).show()
                            }
                        },
                        enabled = customer.currentPoints >= 200,
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = Green, contentColor = Color.White)
                    ) { Text("Redeem 200 Points", fontWeight = FontWeight.Bold) }
                }
            }
        }
        Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF4C8))) {
            Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("How points work", fontWeight = FontWeight.ExtraBold)
                Text("Earn 5 points for every complete ₹100 spent on a bill after discounts. At 200 points, the customer is eligible to redeem the reward at the counter.", fontSize = 13.sp, lineHeight = 19.sp)
                Text("One 200-point redemption is recorded per tap. No cash value is assigned to points in the app.", fontSize = 12.sp, color = Muted)
            }
        }
    }
}

"""
main = once(main, "@Composable\nprivate fun SettingsScreen(",
    loyalty_ui + "@Composable\nprivate fun SettingsScreen(",
    "loyalty customer screen")
MAIN.write_text(main)

gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 4", "versionCode = 5", "app version code")
gradle = once(gradle, 'versionName = "1.4.0"', 'versionName = "1.5.0"', "app version name")
GRADLE.write_text(gradle)

assert (asset_dir / "trivandrum_pork_logo.png").stat().st_size > 10000
assert "loyalty_points_earned" in DATA.read_text()
assert "redeemLoyaltyPoints" in DATA.read_text()
assert "AppScreen.LOYALTY -> LoyaltyScreen" in MAIN.read_text()
assert "SPECIAL DISCOUNT APPLIED" in INVOICE.read_text()
assert "TAKE AWAY" not in INVOICE.read_text()
assert "BILL / INVOICE" not in INVOICE.read_text()
assert "BitmapFactory.decodeStream" in INVOICE.read_text()
assert "Loyalty Points Earned" in EXPORTER.read_text()
assert 'versionName = "1.5.0"' in GRADLE.read_text()
print("v1.5.0 branding, loyalty points, redemption and Excel export updates applied.")
