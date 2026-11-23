package com.trivandrumpork.pos.data

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
    val unitPrice: Int
) {
    val amount: Int get() = quantity * unitPrice
}

data class Bill(
    val id: Long,
    val billNo: String,
    val customerName: String,
    val mobile: String,
    val total: Int,
    val createdAt: Long,
    val items: List<BillLine>
)

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
            FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE
        )""".trimIndent())
        db.execSQL("CREATE TABLE settings (setting_key TEXT PRIMARY KEY, setting_value TEXT NOT NULL)")
        seedProducts(db)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        // Versioned migration point. Existing sales are deliberately never dropped.
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

    fun saveProduct(product: Product): Long {
        val values = ContentValues().apply {
            put("name", product.name.trim()); put("category", product.category); put("price", product.price)
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
        require(lines.isNotEmpty()) { "A bill must contain at least one item" }
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
                }
                db.insertOrThrow("bill_items", null, item)
            }
            db.setTransactionSuccessful()
            return billId
        } finally {
            db.endTransaction()
        }
    }

    fun getBills(limit: Int = 250): List<Bill> {
        val summaries = mutableListOf<Bill>()
        readableDatabase.query("bills", null, null, null, null, null, "created_at DESC", limit.toString()).use { c ->
            while (c.moveToNext()) {
                summaries += Bill(
                    id = c.getLong(c.getColumnIndexOrThrow("id")),
                    billNo = c.getString(c.getColumnIndexOrThrow("bill_no")),
                    customerName = c.getString(c.getColumnIndexOrThrow("customer_name")),
                    mobile = c.getString(c.getColumnIndexOrThrow("mobile")),
                    total = c.getInt(c.getColumnIndexOrThrow("total")),
                    createdAt = c.getLong(c.getColumnIndexOrThrow("created_at")),
                    items = getBillLines(c.getLong(c.getColumnIndexOrThrow("id")))
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
            while (c.moveToNext()) lines += BillLine(
                productName = c.getString(c.getColumnIndexOrThrow("product_name")),
                quantity = c.getInt(c.getColumnIndexOrThrow("quantity")),
                unitPrice = c.getInt(c.getColumnIndexOrThrow("unit_price"))
            )
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
        private const val DB_VERSION = 1
    }
}
