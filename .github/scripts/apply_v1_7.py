from pathlib import Path
import re
ROOT=Path("TrivandrumPorkPOS-Android/app/src/main/java/com/trivandrumpork/pos")
MAIN=ROOT/"MainActivity.kt"
INVOICE=ROOT/"InvoiceImageGenerator.kt"
KITCHEN=ROOT/"KitchenOrderImageGenerator.kt"
GRADLE=Path("TrivandrumPorkPOS-Android/app/build.gradle.kts")
MANIFEST=Path("TrivandrumPorkPOS-Android/app/src/main/AndroidManifest.xml")
RESOURCE=Path("TrivandrumPorkPOS-Android/app/src/main/res/drawable-nodpi/trivandrum_pork_logo.webp")
PATHS=Path("TrivandrumPorkPOS-Android/app/src/main/res/xml/pos_file_paths.xml")

def once(source,old,new,label):
    count=source.count(old)
    if count!=1: raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return source.replace(old,new,1)

def between(source,start_marker,end_marker,replacement,label):
    start=source.find(start_marker)
    end=source.find(end_marker,start+len(start_marker)) if start>=0 else -1
    if start<0 or end<0 or end<=start: raise SystemExit(f"{label}: replacement boundary not found")
    return source[:start]+replacement+source[end:]

if not RESOURCE.exists() or RESOURCE.stat().st_size<1000:
    raise SystemExit("New Trivandrum Pork logo resource missing.")

main=MAIN.read_text()
header="""@Composable
private fun MainHeader(onQuickSettings: () -> Unit) {
    val compact = LocalConfiguration.current.screenWidthDp < 390
    Row(
        Modifier.fillMaxWidth().background(Navy).padding(horizontal = if (compact) 8.dp else 14.dp, vertical = 9.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onQuickSettings, modifier = Modifier.size(34.dp)) {
            Icon(Icons.Filled.Menu, "Quick settings", tint = Color.White, modifier = Modifier.size(24.dp))
        }
        Spacer(Modifier.width(8.dp))
        Image(
            painter = painterResource(id = R.drawable.trivandrum_pork_logo),
            contentDescription = "Trivandrum Pork",
            modifier = Modifier.weight(1f).height(if (compact) 43.dp else 51.dp),
            contentScale = ContentScale.Fit
        )
        IconButton(onClick = onQuickSettings, modifier = Modifier.size(32.dp)) {
            Icon(Icons.Filled.MoreVert, "Settings", tint = Color.White, modifier = Modifier.size(23.dp))
        }
    }
}

"""
main=between(main,"@Composable\nprivate fun MainHeader(","/** A small custom line-art pig mark",header,"replace header logo")

err = "$" + '{e.localizedMessage ?: "Unknown error"}'
old_share = """    fun shareKitchenOrder(bill: Bill) {
        try {
            val imageFile = KitchenOrderImageGenerator(context).generate(bill)
            shareKitchenOrderImage(context, imageFile, settings.kitchenWhatsAppNumber)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create kitchen order image: """ + err + """", Toast.LENGTH_LONG).show()
        }
    }"""
new_share = """    fun shareKitchenOrder(bill: Bill) {
        val imageFile = try {
            KitchenOrderImageGenerator(context).generate(bill)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create kitchen order image: """ + err + """", Toast.LENGTH_LONG).show()
            return
        }
        try {
            shareKitchenOrderImage(context, imageFile, settings.kitchenWhatsAppNumber)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not open kitchen WhatsApp: """ + err + """", Toast.LENGTH_LONG).show()
        }
    }"""
main=once(main,old_share,new_share,"split image generation and WhatsApp handoff errors")
if "kitchenWhatsAppNumber" not in main or "Kitchen WhatsApp Number" not in main:
    raise SystemExit("Kitchen WhatsApp number input missing.")
MAIN.write_text(main)

invoice=INVOICE.read_text()
invoice=once(invoice,"R.drawable.trivandrum_pork_header","R.drawable.trivandrum_pork_logo","replace invoice logo")
INVOICE.write_text(invoice)

kitchen=r'''package com.trivandrumpork.pos
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import com.trivandrumpork.pos.data.Bill
import java.io.File
import java.io.FileOutputStream

/** Only customer name, item names and quantities are drawn on this image. */
class KitchenOrderImageGenerator(private val context: Context) {
    fun generate(bill: Bill): File {
        require(bill.customerName.isNotBlank()) { "Customer name is missing." }
        require(bill.items.isNotEmpty()) { "There are no items in this order." }
        val width=1080
        val height=270+bill.items.size*116
        val bitmap=Bitmap.createBitmap(width,height,Bitmap.Config.ARGB_8888)
        try {
            val canvas=Canvas(bitmap)
            canvas.drawColor(Color.WHITE)
            drawFitted(canvas,bill.customerName.trim(),88f,112f,900f,58f,Color.rgb(23,27,37))
            val divider=Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color=Color.rgb(220,224,230)
                strokeWidth=3f
            }
            canvas.drawLine(88f,158f,992f,158f,divider)
            var rowY=242f
            bill.items.forEachIndexed { index,item ->
                drawFitted(canvas,item.productName,96f,rowY,690f,46f,Color.rgb(27,30,35))
                val quantityPaint=Paint(Paint.ANTI_ALIAS_FLAG).apply {
                    color=Color.rgb(23,27,37)
                    textSize=46f
                    typeface=Typeface.create("sans-serif",Typeface.BOLD)
                    textAlign=Paint.Align.RIGHT
                }
                canvas.drawText("× " + item.quantity.toString(),984f,rowY,quantityPaint)
                if(index<bill.items.lastIndex) canvas.drawLine(96f,rowY+42f,984f,rowY+42f,divider)
                rowY+=116f
            }
            val folder=File(context.cacheDir,"invoices").apply {
                if(!exists() && !mkdirs()) error("Could not create the share folder.")
            }
            val output=File(folder,bill.billNo + "_kitchen.png")
            val saved=FileOutputStream(output).use { bitmap.compress(Bitmap.CompressFormat.PNG,100,it) }
            check(saved && output.isFile && output.length()>0L) { "Kitchen image could not be saved." }
            return output
        } finally {
            bitmap.recycle()
        }
    }
    private fun drawFitted(canvas:Canvas,text:String,x:Float,baseline:Float,maxWidth:Float,size:Float,color:Int) {
        var currentSize=size
        val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply {
            this.color=color
            textSize=currentSize
            typeface=Typeface.create("sans-serif",Typeface.BOLD)
        }
        while(paint.measureText(text)>maxWidth && currentSize>22f) {
            currentSize-=1f
            paint.textSize=currentSize
        }
        var fitted=text
        while(paint.measureText(fitted)>maxWidth && fitted.length>2) fitted=fitted.dropLast(2).trimEnd()+"…"
        canvas.drawText(fitted,x,baseline,paint)
    }
}
'''
KITCHEN.write_text(kitchen)

manifest=MANIFEST.read_text()
provider_pattern=re.compile(r"<provider\b[^>]*(?:/>|>.*?</provider>)",re.S)
target=next((m for m in provider_pattern.finditer(manifest) if "fileprovider" in m.group(0).lower()),None)
metadata='<meta-data android:name="android.support.FILE_PROVIDER_PATHS" android:resource="@xml/pos_file_paths" />'
def set_android_attr(opening,attr,value):
    pattern=re.compile(rf'android:{re.escape(attr)}="[^"]*"')
    replacement=f'android:{attr}="{value}"'
    if pattern.search(opening): return pattern.sub(lambda _m:replacement,opening,count=1)
    return opening[:-1].rstrip()+" "+replacement+">"
if target:
    provider=target.group(0)
    m=re.search(r"<provider\b[^>]*>",provider,re.S)
    if not m: raise SystemExit("Cannot parse FileProvider.")
    opening=m.group(0)
    opening=set_android_attr(opening,"name","androidx.core.content.FileProvider")
    opening=set_android_attr(opening,"authorities",chr(36)+"{applicationId}.fileprovider")
    opening=set_android_attr(opening,"exported","false")
    opening=set_android_attr(opening,"grantUriPermissions","true")
    provider=provider[:m.start()]+opening+provider[m.end():]
    metas=list(re.finditer(r'<meta-data\b[^>]*(?:/>|>.*?</meta-data>)',provider,re.S))
    old=next((x for x in metas if "android.support.FILE_PROVIDER_PATHS" in x.group(0)),None)
    if old: provider=provider[:old.start()]+metadata+provider[old.end():]
    elif provider.rstrip().endswith("/>"): provider=provider.rstrip()[:-2]+">"+metadata+"</provider>"
    else: provider=provider.replace("</provider>",metadata+"</provider>",1)
    manifest=manifest[:target.start()]+provider+manifest[target.end():]
else:
    provider='''<provider
            android:name="androidx.core.content.FileProvider"
            android:authorities="'''+chr(36)+'''{applicationId}.fileprovider"
            android:exported="false"
            android:grantUriPermissions="true">
            '''+metadata+'''
        </provider>'''
    if "</application>" not in manifest: raise SystemExit("No closing application tag.")
    manifest=manifest.replace("</application>",provider+"\n    </application>",1)
if "pos_file_paths" not in manifest: raise SystemExit("FileProvider paths metadata missing.")
MANIFEST.write_text(manifest)
PATHS.parent.mkdir(parents=True,exist_ok=True)
PATHS.write_text('''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="shared_cache" path="." />
    <files-path name="shared_files" path="." />
</paths>
''')

gradle=GRADLE.read_text()
gradle=once(gradle,"versionCode = 6","versionCode = 7","version code")
gradle=once(gradle,'versionName = "1.6.0"','versionName = "1.7.0"',"version name")
GRADLE.write_text(gradle)

assert "Kitchen WhatsApp Number" in MAIN.read_text()
assert "kitchenWhatsAppNumber" in MAIN.read_text()
assert "trivandrum_pork_logo" in MAIN.read_text()
assert "trivandrum_pork_logo" in INVOICE.read_text()
assert "invoices" in KITCHEN.read_text()
assert "CUSTOMER" not in KITCHEN.read_text()
assert "KITCHEN ORDER" not in KITCHEN.read_text()
assert "pos_file_paths" in MANIFEST.read_text()
assert '<cache-path name="shared_cache" path="."' in PATHS.read_text()
assert 'versionName = "1.7.0"' in GRADLE.read_text()
print("v1.7.0 kitchen sharing, FileProvider, and logo fixes applied.")
