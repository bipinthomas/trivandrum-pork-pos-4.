package com.trivandrumpork.pos

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import com.trivandrumpork.pos.data.Bill
import com.trivandrumpork.pos.data.BusinessSettings
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.min

/** Renders a real, shareable PNG invoice directly from the saved sale data. */
class InvoiceImageGenerator(private val context: Context) {
    fun generate(bill: Bill, settings: BusinessSettings): File {
        val width = 1080
        val height = 1320 + bill.items.size * 84
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        canvas.drawColor(Color.rgb(244, 247, 240))

        val yellow = Color.rgb(255, 205, 17)
        val red = Color.rgb(178, 31, 34)
        val navy = Color.rgb(20, 30, 38)
        val black = Color.rgb(20, 22, 25)
        val muted = Color.rgb(95, 101, 108)
        val white = Color.WHITE
        val left = 54f
        val right = 1026f

        // Brand header
        canvas.drawRoundRect(RectF(left, 38f, right, 248f), 42f, 42f, paint(yellow))
        canvas.drawCircle(175f, 139f, 78f, paint(Color.rgb(255, 229, 105)))
        // Compact pig mark: ears, head, snout and eyes.
        canvas.drawOval(RectF(116f, 93f, 153f, 139f), paint(Color.rgb(248, 164, 158)))
        canvas.drawOval(RectF(194f, 93f, 231f, 139f), paint(Color.rgb(248, 164, 158)))
        canvas.drawOval(RectF(122f, 108f, 228f, 190f), paint(Color.rgb(255, 187, 181)))
        canvas.drawRoundRect(RectF(146f, 145f, 204f, 181f), 18f, 18f, paint(Color.rgb(242, 143, 142)))
        // Black sunglasses and a confident smile make the invoice mascot match the shop's playful identity.
        canvas.drawRoundRect(RectF(132f, 125f, 173f, 153f), 8f, 8f, paint(Color.BLACK))
        canvas.drawRoundRect(RectF(181f, 125f, 222f, 153f), 8f, 8f, paint(Color.BLACK))
        canvas.drawLine(171f, 135f, 183f, 135f, strokePaint(Color.BLACK, 8f))
        canvas.drawLine(140f, 131f, 155f, 131f, strokePaint(Color.WHITE, 3f))
        canvas.drawLine(189f, 131f, 204f, 131f, strokePaint(Color.WHITE, 3f))
        canvas.drawCircle(164f, 162f, 4f, paint(Color.rgb(115, 42, 39)))
        canvas.drawCircle(188f, 162f, 4f, paint(Color.rgb(115, 42, 39)))
        canvas.drawArc(RectF(158f, 161f, 194f, 187f), 15f, 150f, false, strokePaint(Color.rgb(115, 42, 39), 4f))
        val brandParts = settings.businessName.trim().split(Regex("\\s+"), limit = 2)
        val brandTop = brandParts.getOrNull(0).orEmpty().ifBlank { "Trivandrum" }
        val brandBottom = brandParts.getOrNull(1).orEmpty().ifBlank { "PORK" }
        canvas.drawText(brandTop, 276f, 130f, textPaint(63f, red, true))
        canvas.drawText(brandBottom.uppercase(Locale.ENGLISH), 276f, 198f, textPaint(72f, black, true))
        canvas.drawText("TAKE AWAY SHOP", 282f, 226f, textPaint(25f, black, true))
        // Minimal coastal Trivandrum landmark silhouettes on the right side of the brand panel.
        val skyline = paint(black)
        canvas.drawRect(RectF(855f, 165f, 995f, 198f), skyline)
        canvas.drawRect(RectF(900f, 92f, 919f, 185f), skyline)
        canvas.drawRect(RectF(894f, 87f, 925f, 96f), skyline)
        canvas.drawPath(android.graphics.Path().apply {
            moveTo(897f, 88f); lineTo(910f, 70f); lineTo(923f, 88f); close()
        }, skyline)
        canvas.drawRect(RectF(906f, 106f, 913f, 120f), paint(yellow))
        canvas.drawPath(android.graphics.Path().apply {
            moveTo(960f, 145f); cubicTo(946f, 126f, 948f, 115f, 956f, 105f)
            moveTo(956f, 105f); cubicTo(938f, 96f, 934f, 90f, 930f, 82f)
            moveTo(956f, 105f); cubicTo(970f, 91f, 978f, 87f, 988f, 86f)
            moveTo(956f, 105f); cubicTo(975f, 103f, 985f, 109f, 991f, 116f)
        }, strokePaint(black, 7f))
        canvas.drawOval(RectF(835f, 192f, 1000f, 214f), paint(black))

        // Invoice title
        canvas.drawRoundRect(RectF(338f, 276f, 742f, 356f), 40f, 40f, paint(red))
        drawCentered(canvas, "BILL / INVOICE", 540f, 333f, 39f, white, true)

        val dateText = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.ENGLISH).format(Date(bill.createdAt))
        canvas.drawText("Bill No  :  ${bill.billNo}", 88f, 422f, textPaint(33f, black, false))
        canvas.drawText("Date      :  $dateText", 88f, 476f, textPaint(31f, black, false))
        canvas.drawRoundRect(RectF(742f, 390f, 985f, 467f), 18f, 18f, strokePaint(red, 4f))
        drawCentered(canvas, "TAKE AWAY", 863f, 440f, 28f, red, true)
        canvas.drawLine(78f, 512f, 1002f, 512f, strokePaint(Color.LTGRAY, 3f))

        canvas.drawText("Customer  :", 88f, 570f, textPaint(31f, black, false))
        drawFitted(canvas, bill.customerName, 300f, 570f, 660f, 33f, black, true)
        canvas.drawText("Mobile      :", 88f, 620f, textPaint(31f, black, false))
        canvas.drawText(bill.mobile, 300f, 620f, textPaint(33f, black, true))
        canvas.drawLine(78f, 652f, 1002f, 652f, strokePaint(Color.LTGRAY, 3f))

        // Items table
        val tableTop = 682f
        canvas.drawRoundRect(RectF(78f, tableTop, 1002f, tableTop + 70f), 16f, 16f, paint(navy))
        canvas.drawText("Item", 110f, tableTop + 47f, textPaint(31f, white, true))
        drawRight(canvas, "Qty", 682f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Price", 830f, tableTop + 47f, 29f, white, true)
        drawRight(canvas, "Amount", 972f, tableTop + 47f, 29f, white, true)

        var rowY = tableTop + 126f
        bill.items.forEachIndexed { index, line ->
            drawFitted(canvas, line.productName, 110f, rowY, 500f, 31f, black, true)
            drawRight(canvas, line.quantity.toString(), 682f, rowY, 30f, black, false)
            drawRight(canvas, rupees(line.unitPrice), 830f, rowY, 30f, black, false)
            drawRight(canvas, rupees(line.amount), 972f, rowY, 30f, black, true)
            canvas.drawLine(100f, rowY + 27f, 980f, rowY + 27f, strokePaint(Color.rgb(219, 222, 224), 2f))
            rowY += 84f
        }

        val totalTop = rowY + 14f
        canvas.drawRoundRect(RectF(78f, totalTop, 1002f, totalTop + 92f), 22f, 22f, paint(Color.rgb(255, 239, 174)))
        canvas.drawText("Total Amount", 112f, totalTop + 61f, textPaint(39f, black, true))
        canvas.drawRoundRect(RectF(730f, totalTop, 1002f, totalTop + 92f), 22f, 22f, paint(red))
        drawCentered(canvas, rupees(bill.total), 866f, totalTop + 63f, 48f, white, true)

        val thankY = totalTop + 174f
        canvas.drawText("Thank You!", 112f, thankY, scriptPaint(57f, red))
        val tag = settings.tagline.ifBlank { "Only for the Real Pork Lovers!" }
        val taglineLines = wrapText(tag, 25).take(2)
        drawCenteredFitted(canvas, taglineLines.getOrElse(0) { tag }, 758f, thankY - if (taglineLines.size > 1) 18f else 6f, 430f, 28f, black, true)
        if (taglineLines.size > 1) drawCenteredFitted(canvas, taglineLines[1], 758f, thankY + 18f, 430f, 28f, black, true)
        canvas.drawLine(635f, thankY + 35f, 888f, thankY + 17f, strokePaint(yellow, 8f))

        val footerTop = height - 170f
        canvas.drawRoundRect(RectF(54f, footerTop, 1026f, height - 35f), 26f, 26f, paint(navy))
        canvas.drawCircle(125f, footerTop + 66f, 35f, paint(Color.rgb(0, 155, 73)))
        drawCentered(canvas, "WA", 125f, footerTop + 78f, 26f, white, true)
        canvas.drawText("FOR ORDERS & ENQUIRIES", 185f, footerTop + 52f, textPaint(24f, white, true))
        val phoneForPrint = if (settings.contactNumber.startsWith("+")) settings.contactNumber else "+91 ${settings.contactNumber}"
        drawFitted(canvas, phoneForPrint, 185f, footerTop + 98f, 345f, 35f, yellow, true)
        canvas.drawLine(565f, footerTop + 25f, 565f, height - 60f, strokePaint(Color.WHITE, 2f))
        canvas.drawCircle(635f, footerTop + 68f, 24f, paint(yellow))
        canvas.drawCircle(635f, footerTop + 68f, 9f, paint(navy))
        val location = settings.location
        val locationLines = splitText(location, 29)
        drawFitted(canvas, locationLines.getOrElse(0) { location }, 680f, footerTop + 57f, 315f, 24f, white, true)
        if (locationLines.size > 1) drawFitted(canvas, locationLines[1], 680f, footerTop + 94f, 315f, 24f, white, true)

        val folder = File(context.cacheDir, "invoices").apply { mkdirs() }
        val output = File(folder, "${bill.billNo}.png")
        FileOutputStream(output).use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
        bitmap.recycle()
        return output
    }

    private fun paint(color: Int) = Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color }
    private fun strokePaint(color: Int, width: Float) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        this.color = color; style = Paint.Style.STROKE; strokeWidth = width
    }
    private fun textPaint(size: Float, color: Int, bold: Boolean) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size; this.color = color
        typeface = Typeface.create("sans-serif", if (bold) Typeface.BOLD else Typeface.NORMAL)
    }
    private fun scriptPaint(size: Float, color: Int) = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textSize = size; this.color = color; typeface = Typeface.create("cursive", Typeface.BOLD)
    }
    private fun drawCentered(canvas: Canvas, text: String, x: Float, y: Float, size: Float, color: Int, bold: Boolean) {
        val p = textPaint(size, color, bold); p.textAlign = Paint.Align.CENTER; canvas.drawText(text, x, y, p)
    }
    private fun drawRight(canvas: Canvas, text: String, x: Float, y: Float, size: Float, color: Int, bold: Boolean) {
        val p = textPaint(size, color, bold); p.textAlign = Paint.Align.RIGHT; canvas.drawText(text, x, y, p)
    }
    private fun drawCenteredFitted(
        canvas: Canvas, text: String, centerX: Float, baseline: Float, maxWidth: Float,
        size: Float, color: Int, bold: Boolean
    ) {
        var currentSize = size
        var p = textPaint(currentSize, color, bold)
        while (p.measureText(text) > maxWidth && currentSize > 17f) {
            currentSize -= 1f
            p = textPaint(currentSize, color, bold)
        }
        p.textAlign = Paint.Align.CENTER
        canvas.drawText(text, centerX, baseline, p)
    }

    private fun drawFitted(
        canvas: Canvas, text: String, x: Float, baseline: Float, maxWidth: Float,
        size: Float, color: Int, bold: Boolean
    ) {
        var currentSize = size
        var p = textPaint(currentSize, color, bold)
        while (p.measureText(text) > maxWidth && currentSize > 17f) {
            currentSize -= 1f
            p = textPaint(currentSize, color, bold)
        }
        var fitted = text
        while (p.measureText(fitted) > maxWidth && fitted.length > 2) {
            fitted = fitted.dropLast(2).trimEnd() + "…"
        }
        canvas.drawText(fitted, x, baseline, p)
    }

    private fun wrapText(text: String, maxChars: Int): List<String> {
        val words = text.trim().split(Regex("\\s+")).filter { it.isNotBlank() }
        val lines = mutableListOf<String>()
        var current = ""
        words.forEach { word ->
            val candidate = if (current.isEmpty()) word else "$current $word"
            if (candidate.length > maxChars && current.isNotEmpty()) {
                lines += current
                current = word
            } else current = candidate
        }
        if (current.isNotEmpty()) lines += current
        return lines
    }

    private fun rupees(value: Int) = "₹${String.format(Locale.ENGLISH, "%,d", value)}"
    private fun splitText(text: String, maxChars: Int): List<String> = if (text.length <= maxChars) listOf(text) else {
        val split = text.lastIndexOf(' ', maxChars).takeIf { it > 0 } ?: maxChars
        listOf(text.substring(0, split), text.substring(split).trim())
    }
}
