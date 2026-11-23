from pathlib import Path
import base64

ROOT = Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
DATA = ROOT / "data" / "PosDatabase.kt"
MAIN = ROOT / "MainActivity.kt"
INVOICE = ROOT / "InvoiceImageGenerator.kt"
EXPORTER = ROOT / "SalesExcelExporter.kt"
GRADLE = Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")
ASSET_B64 = Path(".github/assets/trivandrum_pork_header.webp.b64")
RESOURCE = Path("TrivandrumPorkPOS-Android/app/src/main/res/drawable-nodpi/trivandrum_pork_header.webp")

def once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old, new, 1)

def between(source, start_marker, end_marker, replacement, label):
    start = source.find(start_marker)
    end = source.find(end_marker, start + len(start_marker)) if start >= 0 else -1
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"{label}: replacement boundary not found")
    return source[:start] + replacement + source[end:]


# Install the uploaded Trivandrum Pork header image as a native Android resource.
RESOURCE.parent.mkdir(parents=True, exist_ok=True)
RESOURCE.write_bytes(base64.b64decode(ASSET_B64.read_text().strip(), validate=True))
if RESOURCE.stat().st_size < 1000:
    raise SystemExit("Bill header image failed its size check.")


# Database migration: v2 -> v3; existing sales and settings are retained.
database = DATA.read_text()
database = once(database,
    '''    val items: List<BillLine>
) {
    val totalSavings''',
    '''    val items: List<BillLine>,
    val loyaltyPointsEarned: Int = 0,
    val loyaltyPointsBalance: Int = 0
) {
    val totalSavings''',
    "Bill loyalty fields")
database = once(database, '''data class BusinessSettings(''',
    '''data class LoyaltyCustomer(
    val name: String,
    val mobile: String,
    val points: Int,
    val lifetimeEarned: Int,
    val lifetimeRedeemed: Int,
    val updatedAt: Long
)

data class BusinessSettings(''',
    "LoyaltyCustomer data model")

database = once(database,
    '''            total INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )""".trimIndent())''',
    '''            total INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            loyalty_points_earned INTEGER NOT NULL DEFAULT 0,
            loyalty_points_balance INTEGER NOT NULL DEFAULT 0
        )""".trimIndent())
        db.execSQL("""CREATE TABLE loyalty_customers (
            mobile TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            lifetime_earned INTEGER NOT NULL DEFAULT 0,
            lifetime_redeemed INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL
        )""".trimIndent())''',
    "create loyalty schema")

database = once(database,
    '''        if (oldVersion < 2) {
            createCategoryTables(db)
            db.execSQL("ALTER TABLE bill_items ADD COLUMN original_unit_price INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN category TEXT NOT NULL DEFAULT ''")
            db.execSQL("UPDATE bill_items SET original_unit_price = unit_price WHERE original_unit_price = 0")
            db.execSQL("INSERT OR IGNORE INTO categories(name) SELECT DISTINCT category FROM products WHERE TRIM(category) <> ''")
            db.execSQL("INSERT OR IGNORE INTO categories(name) VALUES('Other')")
        }
    }''',
    '''        if (oldVersion < 2) {
            createCategoryTables(db)
            db.execSQL("ALTER TABLE bill_items ADD COLUMN original_unit_price INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN discount_percent INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bill_items ADD COLUMN category TEXT NOT NULL DEFAULT ''")
            db.execSQL("UPDATE bill_items SET original_unit_price = unit_price WHERE original_unit_price = 0")
            db.execSQL("INSERT OR IGNORE INTO categories(name) SELECT DISTINCT category FROM products WHERE TRIM(category) <> ''")
            db.execSQL("INSERT OR IGNORE INTO categories(name) VALUES('Other')")
        }
        if (oldVersion < 3) {
            db.execSQL("""CREATE TABLE IF NOT EXISTS loyalty_customers (
                mobile TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                lifetime_earned INTEGER NOT NULL DEFAULT 0,
                lifetime_redeemed INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            )""".trimIndent())
            db.execSQL("ALTER TABLE bills ADD COLUMN loyalty_points_earned INTEGER NOT NULL DEFAULT 0")
            db.execSQL("ALTER TABLE bills ADD COLUMN loyalty_points_balance INTEGER NOT NULL DEFAULT 0")
        }
    }''',
    "v3 loyalty migration")

database = once(database,
    '''            val total = lines.sumOf { it.amount }
            val values = ContentValues().apply {
                put("bill_no", billNo); put("customer_name", customerName.trim()); put("mobile", mobile.trim())
                put("total", total); put("created_at", System.currentTimeMillis())
            }''',
    '''            val total = lines.sumOf { it.amount }
            val normalizedMobile = mobile.filter { it.isDigit() }.takeLast(10)
            val pointsEarned = (total.coerceAtLeast(0) / 100) * 5
            var previousPoints = 0
            var lifetimeEarned = 0
            var lifetimeRedeemed = 0
            if (normalizedMobile.length == 10) {
                db.rawQuery(
                    "SELECT points, lifetime_earned, lifetime_redeemed FROM loyalty_customers WHERE mobile=?",
                    arrayOf(normalizedMobile)
                ).use { cursor ->
                    if (cursor.moveToFirst()) {
                        previousPoints = cursor.getInt(0)
                        lifetimeEarned = cursor.getInt(1)
                        lifetimeRedeemed = cursor.getInt(2)
                    }
                }
            }
            val pointsBalance = if (normalizedMobile.length == 10) previousPoints + pointsEarned else 0
            val now = System.currentTimeMillis()
            val values = ContentValues().apply {
                put("bill_no", billNo); put("customer_name", customerName.trim()); put("mobile", mobile.trim())
                put("total", total); put("created_at", now)
                put("loyalty_points_earned", pointsEarned)
                put("loyalty_points_balance", pointsBalance)
            }''',
    "calculate earned points during bill save")

database = once(database,
    '''            db.setTransactionSuccessful()
            return billId''',
    '''            if (normalizedMobile.length == 10) {
                val customerValues = ContentValues().apply {
                    put("mobile", normalizedMobile)
                    put("name", customerName.trim())
                    put("points", pointsBalance)
                    put("lifetime_earned", lifetimeEarned + pointsEarned)
                    put("lifetime_redeemed", lifetimeRedeemed)
                    put("updated_at", now)
                }
                db.insertWithOnConflict("loyalty_customers", null, customerValues, SQLiteDatabase.CONFLICT_REPLACE)
            }
            db.setTransactionSuccessful()
            return billId''',
    "persist customer loyalty points")

database = once(database,
    '''                    createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                    items = getBillLines(id)''',
    '''                    createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                    items = getBillLines(id),
                    loyaltyPointsEarned = c.getInt(c.getColumnIndexOrThrow("loyalty_points_earned")),
                    loyaltyPointsBalance = c.getInt(c.getColumnIndexOrThrow("loyalty_points_balance"))''',
    "read loyalty data in bill history")
database = once(database,
    '''                createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                items = emptyList()''',
    '''                createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                items = emptyList(),
                loyaltyPointsEarned = c.getInt(c.getColumnIndexOrThrow("loyalty_points_earned")),
                loyaltyPointsBalance = c.getInt(c.getColumnIndexOrThrow("loyalty_points_balance"))''',
    "read loyalty data in bill details")

loyalty_methods = '''    fun getLoyaltyCustomers(): List<LoyaltyCustomer> {
        val result = mutableListOf<LoyaltyCustomer>()
        readableDatabase.query("loyalty_customers", null, null, null, null, null, "points DESC, updated_at DESC").use { cursor ->
            while (cursor.moveToNext()) {
                result += LoyaltyCustomer(
                    name = cursor.getString(cursor.getColumnIndexOrThrow("name")),
                    mobile = cursor.getString(cursor.getColumnIndexOrThrow("mobile")),
                    points = cursor.getInt(cursor.getColumnIndexOrThrow("points")),
                    lifetimeEarned = cursor.getInt(cursor.getColumnIndexOrThrow("lifetime_earned")),
                    lifetimeRedeemed = cursor.getInt(cursor.getColumnIndexOrThrow("lifetime_redeemed")),
                    updatedAt = cursor.getLong(cursor.getColumnIndexOrThrow("updated_at"))
                )
            }
        }
        return result
    }

    fun redeemLoyaltyPoints(mobile: String, points: Int = 200): Boolean {
        require(points > 0)
        val normalizedMobile = mobile.filter { it.isDigit() }.takeLast(10)
        if (normalizedMobile.length != 10) return false
        val db = writableDatabase
        db.beginTransaction()
        try {
            var currentPoints = 0
            var lifetimeRedeemed = 0
            db.rawQuery("SELECT points, lifetime_redeemed FROM loyalty_customers WHERE mobile=?", arrayOf(normalizedMobile)).use { cursor ->
                if (!cursor.moveToFirst()) return false
                currentPoints = cursor.getInt(0)
                lifetimeRedeemed = cursor.getInt(1)
            }
            if (currentPoints < points) return false
            val changed = db.update(
                "loyalty_customers",
                ContentValues().apply {
                    put("points", currentPoints - points)
                    put("lifetime_redeemed", lifetimeRedeemed + points)
                    put("updated_at", System.currentTimeMillis())
                },
                "mobile=?", arrayOf(normalizedMobile)
            )
            if (changed != 1) return false
            db.setTransactionSuccessful()
            return true
        } finally {
            db.endTransaction()
        }
    }

'''
database = once(database, "    fun getSales(fromMillis: Long): Pair<Int, Int> {", loyalty_methods + "    fun getSales(fromMillis: Long): Pair<Int, Int> {", "loyalty query and redemption functions")
database = once(database, "private const val DB_VERSION = 2", "private const val DB_VERSION = 3", "DB schema version")
DATA.write_text(database)


# Bill image: use uploaded brand artwork and remove the old Take Away/Invoice labels.
invoice = INVOICE.read_text()
invoice = once(invoice, "import android.graphics.Bitmap\n", "import android.graphics.Bitmap\nimport android.graphics.BitmapFactory\n", "BitmapFactory import")
header = '''        // Uploaded Trivandrum Pork brand banner
        canvas.drawRoundRect(RectF(left, 38f, right, 248f), 36f, 36f, paint(Color.WHITE))
        val headerBitmap = BitmapFactory.decodeResource(context.resources, R.drawable.trivandrum_pork_header)
            ?: error("Trivandrum Pork bill header image could not be loaded.")
        val logoHeight = 198f
        val logoWidth = logoHeight * headerBitmap.width.toFloat() / headerBitmap.height.toFloat()
        val logoLeft = (width - logoWidth) / 2f
        canvas.drawBitmap(headerBitmap, null, RectF(logoLeft, 43f, logoLeft + logoWidth, 43f + logoHeight),
            Paint(Paint.ANTI_ALIAS_FLAG).apply { isFilterBitmap = true })
        headerBitmap.recycle()

'''
invoice = between(invoice, "        // Brand header", "        // Invoice title", header, "replace bill image header")
invoice = once(invoice,
    'drawCentered(canvas, "BILL / INVOICE", 540f, 333f, 39f, white, true)',
    'drawCentered(canvas, "BILL", 540f, 333f, 39f, white, true)',
    "remove Invoice heading")
invoice = once(invoice,
    '''        canvas.drawRoundRect(RectF(742f, 390f, 985f, 467f), 18f, 18f, strokePaint(red, 4f))
        drawCentered(canvas, "TAKE AWAY", 863f, 440f, 28f, red, true)
''',
    "",
    "remove Take Away box")
invoice = once(invoice,
    '"YOU SAVED " + rupees(savings) + " WITH CATEGORY DISCOUNTS!"',
    '"Special discount applied, you saved " + rupees(savings) + "/-"',
    "discount line wording")
INVOICE.write_text(invoice)


# Excel report: a points summary, plus one bill-level entry per bill in the detail.
exporter = EXPORTER.read_text()
exporter = once(exporter,
    '        rows += listOf("Net Sales", netSales)\n        rows.add(emptyList())',
    '        rows += listOf("Net Sales", netSales)\n        rows += listOf("Total Loyalty Points Earned", bills.sumOf { it.loyaltyPointsEarned })\n        rows.add(emptyList())',
    "Excel points summary")
exporter = once(exporter,
    'rows += listOf("Bill No", "Date", "Customer", "Mobile", "Category", "Item", "Qty", "Original Rate", "Discount %", "Discounted Rate", "Original Amount", "Discount Amount", "Net Amount")',
    'rows += listOf("Bill No", "Date", "Customer", "Mobile", "Category", "Item", "Qty", "Original Rate", "Discount %", "Discounted Rate", "Original Amount", "Discount Amount", "Net Amount", "Loyalty Points Earned", "Points Balance")',
    "Excel loyalty detail columns")
old_rows = '''        bills.forEach { bill ->
            bill.items.forEach { line ->
                rows += listOf(bill.billNo, dateFormat.format(Date(bill.createdAt)), bill.customerName, bill.mobile,
                    line.category, line.productName, line.quantity, line.originalUnitPrice, line.discountPercent,
                    line.unitPrice, line.originalAmount, line.discountAmount, line.amount)
            }
        }'''
new_rows = '''        bills.forEach { bill ->
            bill.items.forEachIndexed { itemIndex, line ->
                // Bill-level loyalty totals appear only once, avoiding duplicated sums for multi-item bills.
                rows += listOf(bill.billNo, dateFormat.format(Date(bill.createdAt)), bill.customerName, bill.mobile,
                    line.category, line.productName, line.quantity, line.originalUnitPrice, line.discountPercent,
                    line.unitPrice, line.originalAmount, line.discountAmount, line.amount,
                    if (itemIndex == 0) bill.loyaltyPointsEarned else "",
                    if (itemIndex == 0) bill.loyaltyPointsBalance else "")
            }
        }'''
exporter = once(exporter, old_rows, new_rows, "Excel bill rows with points")
exporter = once(exporter,
    "val widths = listOf(18, 24, 24, 18, 18, 28, 10, 15, 12, 17, 18, 18, 18)",
    "val widths = listOf(18, 24, 24, 18, 18, 28, 10, 15, 12, 17, 18, 18, 18, 20, 16)",
    "Excel loyalty widths")
if exporter.count("A13:M") != 1:
    raise SystemExit("Excel filter range: expected one A13:M reference.")
exporter = exporter.replace("A13:M", "A13:O", 1)
EXPORTER.write_text(exporter)


# Main app: show balances, redeem at the counter, and notify customers through WhatsApp.
main = MAIN.read_text()
main = once(main,
    "import com.trivandrumpork.pos.data.BillLine\n",
    "import com.trivandrumpork.pos.data.BillLine\nimport com.trivandrumpork.pos.data.LoyaltyCustomer\n",
    "LoyaltyCustomer import")
main = once(main,
    "private enum class AppScreen { POS, BILLS, MENU, SALES, SETTINGS, ADD_ITEM, BILL_DETAIL }",
    "private enum class AppScreen { POS, BILLS, MENU, SALES, LOYALTY, SETTINGS, ADD_ITEM, BILL_DETAIL }",
    "loyalty screen enum")
main = once(main,
    "    var bills by remember { mutableStateOf(db.getBills()) }\n",
    "    var bills by remember { mutableStateOf(db.getBills()) }\n    var loyaltyCustomers by remember { mutableStateOf(db.getLoyaltyCustomers()) }\n",
    "loyalty app state")
main = once(main,
    "        bills = db.getBills()\n        settings = db.getSettings()",
    "        bills = db.getBills()\n        loyaltyCustomers = db.getLoyaltyCustomers()\n        settings = db.getSettings()",
    "refresh loyalty state")

main = once(main,
    "shareBill(newBill)",
    """if (newBill.loyaltyPointsBalance >= 200) {
                                        Toast.makeText(
                                            context,
                                            newBill.customerName + " has reached " + newBill.loyaltyPointsBalance +
                                                " loyalty points and can redeem 200 points at the counter.",
                                            Toast.LENGTH_LONG
                                        ).show()
                                    }
                                    shareBill(newBill)""",
    "notify cashier at 200 points")

nav_start = main.find("private fun MainNavigation(")
nav_end = main.find("\n@Composable\nprivate fun SubHeader", nav_start)
if nav_start < 0 or nav_end < 0:
    raise SystemExit("MainNavigation block was not found.")
navigation = main[nav_start:nav_end]
navigation = once(navigation,
    '        Triple(AppScreen.SALES, "Sales", Icons.Filled.BarChart),',
    '        Triple(AppScreen.SALES, "Sales", Icons.Filled.BarChart),\n        Triple(AppScreen.LOYALTY, "Loyalty", Icons.Filled.Person),',
    "add Loyalty tab")
navigation = once(navigation, "Modifier.size(25.dp)", "Modifier.size(22.dp)", "six-tab icon sizing")
navigation = once(navigation,
    "fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 1",
    "fontSize = 10.sp, fontWeight = FontWeight.SemiBold, maxLines = 1",
    "six-tab label sizing")
main = main[:nav_start] + navigation + main[nav_end:]

main = once(main,
    "                    AppScreen.SETTINGS -> SettingsScreen(",
    '''                    AppScreen.LOYALTY -> LoyaltyScreen(
                        customers = loyaltyCustomers,
                        onRedeem = { mobile ->
                            val redeemed = db.redeemLoyaltyPoints(mobile, 200)
                            refresh()
                            Toast.makeText(
                                context,
                                if (redeemed) "200 loyalty points redeemed successfully." else "Customer does not have 200 points available.",
                                Toast.LENGTH_LONG
                            ).show()
                        }
                    )
                    AppScreen.SETTINGS -> SettingsScreen(''',
    "loyalty screen routing")

loyalty_screen = '''@Composable
private fun LoyaltyScreen(customers: List<LoyaltyCustomer>, onRedeem: (String) -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(horizontal = 14.dp, vertical = 12.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("Customer Loyalty", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
        Text("Earn 5 points for every Rs.100 spent. Redeem 200 points at the counter.", color = Muted, fontSize = 13.sp)
        if (customers.isEmpty()) {
            EmptyState("No loyalty customers yet", "Points are added automatically when a bill is saved with a valid mobile number.")
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                items(customers, key = { it.mobile }) { customer ->
                    Card(
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = Color.White),
                        elevation = CardDefaults.cardElevation(2.dp)
                    ) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(customer.name, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                                    Text(customer.mobile, color = Muted, fontSize = 12.sp)
                                }
                                Text(customer.points.toString() + " pts", color = Green, fontWeight = FontWeight.ExtraBold, fontSize = 22.sp)
                            }
                            Text("Lifetime earned: " + customer.lifetimeEarned + "  •  Redeemed: " + customer.lifetimeRedeemed, color = Muted, fontSize = 12.sp)
                            if (customer.points >= 200) {
                                Text("Eligible to redeem 200 points at the counter.", color = Green, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                                Button(
                                    onClick = { onRedeem(customer.mobile) },
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink),
                                    shape = RoundedCornerShape(11.dp)
                                ) { Text("Redeem 200 Points", fontWeight = FontWeight.ExtraBold) }
                            } else {
                                Text((200 - customer.points).toString() + " more points to reach the 200-point reward.", color = Muted, fontSize = 12.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

'''
main = once(main, "@Composable\nprivate fun BackupRestoreCard(", loyalty_screen + "@Composable\nprivate fun BackupRestoreCard(", "loyalty customer screen")

old_share_text = (
    'putExtra(Intent.EXTRA_TEXT, "Thank you for ordering from ' + '$' + '{settings.businessName}!\\nBill: ' +
    '$' + '{bill.billNo}\\nTotal: ' + '$' + '{rupees(bill.total)}")'
)
new_share_text = '''val loyaltyNotice = if (bill.loyaltyPointsBalance >= 200) "\\nCongratulations! You have reached 200 loyalty points. You can redeem 200 points at the counter." else ""
                  putExtra(
                      Intent.EXTRA_TEXT,
                      "Thank you for ordering from " + settings.businessName + "!\\nBill: " + bill.billNo +
                          "\\nTotal: " + rupees(bill.total) +
                          "\\nLoyalty points earned: " + bill.loyaltyPointsEarned +
                          "\\nYour loyalty points balance: " + bill.loyaltyPointsBalance + loyaltyNotice
                  )'''
main = once(main, old_share_text, new_share_text, "WhatsApp customer loyalty notification")
MAIN.write_text(main)


# Raise Android version for an installable upgrade.
gradle = GRADLE.read_text()
gradle = once(gradle, "versionCode = 5", "versionCode = 6", "Android versionCode")
gradle = once(gradle, 'versionName = "1.5.0"', 'versionName = "1.6.0"', "Android versionName")
GRADLE.write_text(gradle)


# Refuse to complete the workflow if a requested feature was not added.
assert "loyalty_customers" in DATA.read_text()
assert "redeemLoyaltyPoints" in DATA.read_text()
assert "loyaltyPointsEarned" in DATA.read_text()
assert "Special discount applied, you saved " in INVOICE.read_text()
assert 'drawCentered(canvas, "BILL", 540f' in INVOICE.read_text()
assert '"TAKE AWAY"' not in INVOICE.read_text()
assert "R.drawable.trivandrum_pork_header" in INVOICE.read_text()
assert "LoyaltyScreen" in MAIN.read_text()
assert "Loyalty Points Earned" in EXPORTER.read_text()
assert 'versionName = "1.6.0"' in GRADLE.read_text()
print("v1.6.0 bill branding, discount wording, loyalty earning/redemption and Excel updates applied.")
