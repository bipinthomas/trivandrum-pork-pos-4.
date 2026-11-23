package com.trivandrumpork.pos

import android.content.ClipData
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Remove
import androidx.compose.material.icons.filled.Restaurant
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.FileProvider
import com.trivandrumpork.pos.data.Bill
import com.trivandrumpork.pos.data.BillLine
import com.trivandrumpork.pos.data.BusinessSettings
import com.trivandrumpork.pos.data.PosDatabase
import com.trivandrumpork.pos.data.Product
import java.io.File
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Date
import java.util.Locale

private val Navy = Color(0xFF171B25)
private val Yellow = Color(0xFFFFC914)
private val Red = Color(0xFFAA2223)
private val Green = Color(0xFF078B39)
private val Page = Color(0xFFF3F5F7)
private val Ink = Color(0xFF17191D)
private val Muted = Color(0xFF6C727B)
private val Line = Color(0xFFE1E4E8)
private val Cream = Color(0xFFFFF6D9)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = android.graphics.Color.rgb(23, 27, 37)
        window.navigationBarColor = android.graphics.Color.rgb(243, 245, 247)
        window.decorView.systemUiVisibility = 0x00002000 // light navigation bar icons
        val database = PosDatabase(applicationContext)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Yellow,
                    onPrimary = Ink,
                    secondary = Red,
                    background = Page,
                    surface = Color.White,
                    onSurface = Ink
                )
            ) {
                PorkPosApp(database)
            }
        }
    }
}

private enum class AppScreen { POS, BILLS, MENU, SALES, SETTINGS, ADD_ITEM, BILL_DETAIL }

@Composable
private fun PorkPosApp(db: PosDatabase) {
    val context = LocalContext.current
    var screen by rememberSaveable { mutableStateOf(AppScreen.POS) }
    var products by remember { mutableStateOf(db.getProducts()) }
    var bills by remember { mutableStateOf(db.getBills()) }
    var settings by remember { mutableStateOf(db.getSettings()) }
    var editProduct by remember { mutableStateOf<Product?>(null) }
    var selectedBill by remember { mutableStateOf<Bill?>(null) }
    var posCategory by rememberSaveable { mutableStateOf("All") }
    var menuCategory by rememberSaveable { mutableStateOf("All") }
    var customerName by rememberSaveable { mutableStateOf("") }
    var customerMobile by rememberSaveable { mutableStateOf("") }
    val cart = remember { mutableStateMapOf<Long, Int>() }
    var deleteCandidate by remember { mutableStateOf<Product?>(null) }

    fun refresh() {
        products = db.getProducts()
        bills = db.getBills()
        settings = db.getSettings()
    }

    fun shareBill(bill: Bill) {
        try {
            val imageFile = InvoiceImageGenerator(context).generate(bill, settings)
            shareInvoiceImage(context, imageFile, bill, settings)
        } catch (e: Exception) {
            Toast.makeText(context, "Could not create invoice image: ${e.localizedMessage ?: "Unknown error"}", Toast.LENGTH_LONG).show()
        }
    }

    Column(Modifier.fillMaxSize().background(Page)) {
        if (screen == AppScreen.ADD_ITEM || screen == AppScreen.BILL_DETAIL) {
            SubHeader(
                title = if (screen == AppScreen.ADD_ITEM) if (editProduct == null) "Add Menu Item" else "Edit Menu Item" else "Bill Details",
                onBack = { screen = if (screen == AppScreen.ADD_ITEM) AppScreen.MENU else AppScreen.BILLS }
            )
        } else {
            MainHeader(onQuickSettings = { screen = AppScreen.SETTINGS })
            MainNavigation(selected = screen, onSelect = { screen = it })
        }

        Box(Modifier.weight(1f).fillMaxWidth()) {
            AnimatedContent(
                targetState = screen,
                transitionSpec = {
                    (fadeIn() + slideInHorizontally { it / 18 }) togetherWith
                        (fadeOut() + slideOutHorizontally { -it / 24 })
                },
                label = "screen-transition"
            ) { target ->
                when (target) {
                    AppScreen.POS -> PosScreen(
                        products = products.filter { it.active }, category = posCategory,
                        onCategory = { posCategory = it }, cart = cart, customerName = customerName,
                        onCustomerName = { customerName = it }, mobile = customerMobile,
                        onMobile = { customerMobile = it }, onSave = {
                            val selectedLines = cart.entries.mapNotNull { (id, qty) ->
                                val product = products.firstOrNull { it.id == id }
                                if (product == null || qty < 1) null else BillLine(product.name, qty, product.price)
                            }
                            if (selectedLines.isEmpty()) {
                                Toast.makeText(context, "Add at least one product to the cart", Toast.LENGTH_SHORT).show()
                            } else if (customerName.isBlank() || customerMobile.filter { it.isDigit() }.length < 10) {
                                Toast.makeText(context, "Enter customer name and a valid mobile number", Toast.LENGTH_SHORT).show()
                            } else {
                                try {
                                    val id = db.saveBill(customerName, customerMobile, selectedLines, settings)
                                    val newBill = db.getBill(id) ?: error("Saved bill could not be loaded")
                                    refresh()
                                    cart.clear()
                                    customerName = ""
                                    customerMobile = ""
                                    shareBill(newBill)
                                    Toast.makeText(context, "${newBill.billNo} saved successfully", Toast.LENGTH_SHORT).show()
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Unable to save bill: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                                }
                            }
                        },
                        onAdd = { id -> cart[id] = (cart[id] ?: 0) + 1 },
                        onQuantity = { id, qty -> if (qty <= 0) cart.remove(id) else cart[id] = qty },
                        onClear = { cart.clear() }
                    )
                    AppScreen.MENU -> MenuScreen(
                        products = products, category = menuCategory, onCategory = { menuCategory = it },
                        onAdd = { editProduct = null; screen = AppScreen.ADD_ITEM },
                        onEdit = { editProduct = it; screen = AppScreen.ADD_ITEM },
                        onToggle = { product, enabled -> db.setProductActive(product.id, enabled); refresh() },
                        onDelete = { deleteCandidate = it }
                    )
                    AppScreen.ADD_ITEM -> key(editProduct?.id ?: 0L) {
                        AddItemScreen(
                            product = editProduct,
                            onCancel = { screen = AppScreen.MENU },
                            onSave = { product ->
                                db.saveProduct(product)
                                refresh()
                                screen = AppScreen.MENU
                                Toast.makeText(context, "Menu item saved", Toast.LENGTH_SHORT).show()
                            }
                        )
                    }
                    AppScreen.BILLS -> BillsScreen(bills = bills, onOpen = { bill -> selectedBill = bill; screen = AppScreen.BILL_DETAIL }, onShare = ::shareBill)
                    AppScreen.BILL_DETAIL -> selectedBill?.let { bill ->
                        BillDetailsScreen(bill = db.getBill(bill.id) ?: bill, settings = settings, onShare = { shareBill(db.getBill(bill.id) ?: bill) })
                    } ?: EmptyState("Bill not found", "Return to Bills to choose another invoice")
                    AppScreen.SALES -> SalesScreen(db = db, bills = bills)
                    AppScreen.SETTINGS -> SettingsScreen(settings = settings, onSave = { updated -> db.saveSettings(updated); settings = updated; Toast.makeText(context, "Settings saved", Toast.LENGTH_SHORT).show() })
                }
            }
        }
    }

    deleteCandidate?.let { product ->
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
private fun MainHeader(onQuickSettings: () -> Unit) {
    val compact = LocalConfiguration.current.screenWidthDp < 390
    Row(
        Modifier.fillMaxWidth().background(Navy).padding(horizontal = if (compact) 8.dp else 14.dp, vertical = 11.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(onClick = onQuickSettings, modifier = Modifier.size(34.dp)) {
            Icon(Icons.Filled.Menu, "Quick settings", tint = Color.White, modifier = Modifier.size(24.dp))
        }
        Spacer(Modifier.width(if (compact) 4.dp else 9.dp))
        BrandPigMark(Modifier.size(if (compact) 43.dp else 50.dp))
        Spacer(Modifier.width(7.dp))
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.weight(1f)) {
            Text("Trivandrum", color = Color.White, fontSize = if (compact) 16.sp else 18.sp, fontWeight = FontWeight.Bold, maxLines = 1)
            Spacer(Modifier.width(4.dp))
            Text("Pork POS", color = Yellow, fontSize = if (compact) 17.sp else 20.sp, fontWeight = FontWeight.ExtraBold, maxLines = 1)
        }
        IconButton(onClick = onQuickSettings, modifier = Modifier.size(32.dp)) {
            Icon(Icons.Filled.MoreVert, "Settings", tint = Color.White, modifier = Modifier.size(23.dp))
        }
    }
}

/** A small custom line-art pig mark matching the yellow-on-navy reference branding. */
@Composable
private fun BrandPigMark(modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val stroke = Stroke(width = w * .075f, cap = StrokeCap.Round, join = StrokeJoin.Round)
        val outline = Path().apply {
            moveTo(w * .21f, h * .36f)
            cubicTo(w * .13f, h * .22f, w * .13f, h * .12f, w * .19f, h * .09f)
            cubicTo(w * .26f, h * .07f, w * .32f, h * .17f, w * .35f, h * .25f)
            cubicTo(w * .47f, h * .19f, w * .64f, h * .20f, w * .74f, h * .27f)
            cubicTo(w * .78f, h * .16f, w * .87f, h * .07f, w * .93f, h * .11f)
            cubicTo(w * .98f, h * .16f, w * .91f, h * .29f, w * .84f, h * .39f)
            cubicTo(w * .91f, h * .49f, w * .91f, h * .66f, w * .82f, h * .74f)
            lineTo(w * .80f, h * .89f)
            lineTo(w * .70f, h * .89f)
            lineTo(w * .69f, h * .78f)
            cubicTo(w * .55f, h * .84f, w * .42f, h * .84f, w * .31f, h * .78f)
            lineTo(w * .29f, h * .89f)
            lineTo(w * .19f, h * .89f)
            lineTo(w * .18f, h * .73f)
            cubicTo(w * .10f, h * .66f, w * .10f, h * .48f, w * .21f, h * .36f)
            close()
        }
        drawPath(outline, Yellow, style = stroke)
        val snout = Path().apply {
            moveTo(w * .79f, h * .48f)
            cubicTo(w * .92f, h * .44f, w * .98f, h * .52f, w * .94f, h * .62f)
            cubicTo(w * .91f, h * .70f, w * .81f, h * .69f, w * .77f, h * .62f)
        }
        drawPath(snout, Yellow, style = stroke)
        drawCircle(Yellow, w * .025f, Offset(w * .83f, h * .55f))
        drawCircle(Yellow, w * .025f, Offset(w * .90f, h * .55f))
    }
}

@Composable
private fun MainNavigation(selected: AppScreen, onSelect: (AppScreen) -> Unit) {
    val tabs = listOf(
        Triple(AppScreen.POS, "POS", Icons.Filled.ShoppingCart),
        Triple(AppScreen.BILLS, "Bills", Icons.Filled.ReceiptLong),
        Triple(AppScreen.MENU, "Menu", Icons.Filled.Restaurant),
        Triple(AppScreen.SALES, "Sales", Icons.Filled.BarChart),
        Triple(AppScreen.SETTINGS, "Settings", Icons.Filled.Settings)
    )
    Row(Modifier.fillMaxWidth().background(Navy).padding(horizontal = 6.dp, vertical = 7.dp), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
        tabs.forEach { (screen, title, icon) ->
            val active = screen == selected
            Column(
                Modifier.weight(1f).clip(RoundedCornerShape(15.dp)).background(if (active) Yellow else Color.Transparent)
                    .clickable { onSelect(screen) }.padding(vertical = 7.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                Icon(icon, contentDescription = title, tint = if (active) Ink else Color(0xFFE5E7EB), modifier = Modifier.size(25.dp))
                Text(title, color = if (active) Ink else Color.White, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 1)
                Spacer(Modifier.height(3.dp))
                Box(
                    Modifier.fillMaxWidth(.82f).height(4.dp).clip(RoundedCornerShape(topStart = 5.dp, topEnd = 5.dp))
                        .background(if (active) Red else Color.Transparent)
                )
            }
        }
    }
}

@Composable
private fun SubHeader(title: String, onBack: () -> Unit) {
    Row(Modifier.fillMaxWidth().background(Navy).padding(horizontal = 12.dp, vertical = 18.dp), verticalAlignment = Alignment.CenterVertically) {
        IconButton(onClick = onBack) { Icon(Icons.Filled.ArrowBack, null, tint = Color.White) }
        Text(title, color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun PosScreen(
    products: List<Product>, category: String, onCategory: (String) -> Unit,
    cart: Map<Long, Int>, customerName: String, onCustomerName: (String) -> Unit,
    mobile: String, onMobile: (String) -> Unit, onSave: () -> Unit,
    onAdd: (Long) -> Unit, onQuantity: (Long, Int) -> Unit, onClear: () -> Unit
) {
    val categories = listOf("All", "Vindaloo", "Roast", "Fry")
    val columns = if (LocalConfiguration.current.screenWidthDp < 360) 2 else 3
    val filtered = if (category == "All") products else products.filter { it.category.equals(category, true) }
    val cartProducts = cart.entries.mapNotNull { entry -> products.firstOrNull { it.id == entry.key }?.let { it to entry.value } }
    val total = cartProducts.sumOf { (product, qty) -> product.price * qty }

    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 12.dp, vertical = 11.dp)) {
        if (LocalConfiguration.current.screenWidthDp < 410) {
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("Select Product", fontSize = 21.sp, fontWeight = FontWeight.ExtraBold, color = Ink)
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    categories.forEach { c -> CategoryChip(c, selected = category == c, onClick = { onCategory(c) }) }
                }
            }
        } else {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
                Text("Select Product", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, color = Ink, maxLines = 1)
                Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    categories.forEach { c -> CategoryChip(c, selected = category == c, onClick = { onCategory(c) }) }
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        if (filtered.isEmpty()) {
            EmptyState("No active products", "Add or activate products from the Menu screen")
        } else {
            val rows = filtered.chunked(columns)
            rows.forEachIndexed { index, row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    row.forEach { product ->
                        ProductTile(product, selected = (cart[product.id] ?: 0) > 0, onAdd = { onAdd(product.id) }, modifier = Modifier.weight(1f))
                    }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
                if (index != rows.lastIndex) Spacer(Modifier.height(9.dp))
            }
        }
        Spacer(Modifier.height(15.dp))
        Card(
            modifier = Modifier.animateContentSize(),
            shape = RoundedCornerShape(22.dp),
            colors = CardDefaults.cardColors(containerColor = Color.White),
            elevation = CardDefaults.cardElevation(2.dp)
        ) {
            Column(Modifier.padding(14.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Order Cart", fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
                    Text(" (${cartProducts.sumOf { it.second }} items)", fontSize = 16.sp, color = Muted)
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onClear, enabled = cart.isNotEmpty()) {
                        Icon(Icons.Filled.Delete, null, tint = Red, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(3.dp)); Text("Clear", color = Red, fontWeight = FontWeight.Bold)
                    }
                }
                if (cartProducts.isEmpty()) {
                    Text("Your cart is empty. Tap + on a product to add it.", color = Muted, fontSize = 13.sp, modifier = Modifier.padding(vertical = 12.dp))
                } else {
                    cartProducts.forEachIndexed { index, (product, qty) ->
                        CartLine(
                            product, qty, compact = LocalConfiguration.current.screenWidthDp < 390,
                            onMinus = { onQuantity(product.id, qty - 1) }, onPlus = { onQuantity(product.id, qty + 1) }
                        )
                        if (index != cartProducts.lastIndex) Divider(color = Line)
                    }
                }
                Spacer(Modifier.height(10.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(15.dp)).background(Cream).padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("Total Amount", fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
                    Spacer(Modifier.weight(1f))
                    Text(rupees(total), fontSize = 28.sp, color = Red, fontWeight = FontWeight.ExtraBold)
                }
            }
        }
        Spacer(Modifier.height(16.dp))
        Text("Customer Details", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(start = 3.dp, bottom = 9.dp))
        if (LocalConfiguration.current.screenWidthDp < 375) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = customerName, onValueChange = onCustomerName, modifier = Modifier.fillMaxWidth(),
                    label = { Text("Name") }, leadingIcon = { Icon(Icons.Filled.Person, null, tint = Muted) },
                    singleLine = true, shape = RoundedCornerShape(15.dp)
                )
                OutlinedTextField(
                    value = mobile, onValueChange = { onMobile(it.filter { ch -> ch.isDigit() || ch == '+' }.take(15)) }, modifier = Modifier.fillMaxWidth(),
                    label = { Text("Mobile Number") }, leadingIcon = { Icon(Icons.Filled.Phone, null, tint = Muted) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(15.dp)
                )
            }
        } else {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = customerName, onValueChange = onCustomerName, modifier = Modifier.weight(1f),
                    label = { Text("Name") }, leadingIcon = { Icon(Icons.Filled.Person, null, tint = Muted) },
                    singleLine = true, shape = RoundedCornerShape(15.dp)
                )
                OutlinedTextField(
                    value = mobile, onValueChange = { onMobile(it.filter { ch -> ch.isDigit() || ch == '+' }.take(15)) }, modifier = Modifier.weight(1f),
                    label = { Text("Mobile Number") }, leadingIcon = { Icon(Icons.Filled.Phone, null, tint = Muted) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(15.dp)
                )
            }
        }
        Spacer(Modifier.height(14.dp))
        Button(
            onClick = onSave, modifier = Modifier.fillMaxWidth().height(62.dp),
            shape = RoundedCornerShape(16.dp), colors = ButtonDefaults.buttonColors(containerColor = Green, contentColor = Color.White)
        ) {
            Icon(Icons.Filled.Chat, contentDescription = "WhatsApp", modifier = Modifier.size(28.dp))
            Spacer(Modifier.width(10.dp))
            Text("Save & Send via WhatsApp", fontSize = if (LocalConfiguration.current.screenWidthDp < 380) 16.sp else 18.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun CategoryChip(text: String, selected: Boolean, onClick: () -> Unit) {
    FilterChip(
        selected = selected, onClick = onClick,
        label = { Text(text, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, modifier = Modifier.padding(horizontal = 2.dp)) },
        colors = androidx.compose.material3.FilterChipDefaults.filterChipColors(
            selectedContainerColor = Yellow, selectedLabelColor = Ink,
            containerColor = Color(0xFFF0F2F4), labelColor = Ink
        ),
        border = BorderStroke(1.dp, if (selected) Yellow else Color(0xFFDCE0E4))
    )
}

@Composable
private fun ProductTile(product: Product, selected: Boolean, onAdd: () -> Unit, modifier: Modifier = Modifier) {
    val tileColor by animateColorAsState(if (selected) Cream else Color.White, label = "product-tile-color")
    val tileBorder by animateColorAsState(if (selected) Yellow else Line, label = "product-tile-border")
    val tileElevation by animateDpAsState(if (selected) 4.dp else 2.dp, label = "product-tile-elevation")
    Card(
        modifier = modifier.height(if (LocalConfiguration.current.screenWidthDp < 360) 164.dp else 174.dp), onClick = onAdd,
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = tileColor),
        border = BorderStroke(if (selected) 1.5.dp else 1.dp, tileBorder),
        elevation = CardDefaults.cardElevation(tileElevation)
    ) {
        Column(Modifier.fillMaxSize().padding(horizontal = 6.dp, vertical = 8.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Box {
                ProductImage(product, Modifier.size(76.dp).clip(RoundedCornerShape(13.dp)))
                if (selected) Box(Modifier.align(Alignment.TopEnd).padding(2.dp).size(20.dp).clip(CircleShape).background(Yellow), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.Check, null, tint = Ink, modifier = Modifier.size(14.dp))
                }
            }
            Text(product.name, fontSize = 14.sp, lineHeight = 16.sp, fontWeight = FontWeight.Bold, color = Ink, maxLines = 2, textAlign = TextAlign.Center, modifier = Modifier.weight(1f).padding(top = 5.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(rupees(product.price), color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                Surface(onClick = onAdd, shape = CircleShape, color = Yellow, modifier = Modifier.size(36.dp)) {
                    Box(contentAlignment = Alignment.Center) { Icon(Icons.Filled.Add, null, tint = Ink, modifier = Modifier.size(23.dp)) }
                }
            }
        }
    }
}

@Composable
private fun ProductImage(product: Product, modifier: Modifier = Modifier) {
    val path = product.imageRef
    val bitmap = remember(path) {
        if (path.startsWith("/") && File(path).exists()) BitmapFactory.decodeFile(path) else null
    }
    if (bitmap != null) {
        Image(bitmap.asImageBitmap(), contentDescription = product.name, modifier = modifier, contentScale = ContentScale.Crop)
    } else {
        val resource = when {
            path == "pork_vindaloo" || product.category.equals("Vindaloo", true) -> R.drawable.pork_vindaloo
            path == "pork_roast" || product.category.equals("Roast", true) -> R.drawable.pork_roast
            path == "pork_fry" || product.category.equals("Fry", true) -> R.drawable.pork_fry
            else -> null
        }
        if (resource != null) Image(painterResource(resource), contentDescription = product.name, modifier = modifier, contentScale = ContentScale.Crop)
        else Box(modifier.background(Color(0xFFFFF0C3)), contentAlignment = Alignment.Center) {
            Icon(Icons.Filled.Restaurant, null, tint = Red, modifier = Modifier.size(36.dp))
        }
    }
}

@Composable
private fun CartLine(
    product: Product,
    quantity: Int,
    compact: Boolean,
    onMinus: () -> Unit,
    onPlus: () -> Unit
) {
    if (compact) {
        Row(
            Modifier.fillMaxWidth().heightIn(min = 58.dp).padding(vertical = 7.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Column(Modifier.weight(1f)) {
                Text(product.name, fontSize = 13.sp, fontWeight = FontWeight.Bold, maxLines = 2, lineHeight = 15.sp)
                Text(rupees(product.price), fontSize = 12.sp, color = Muted)
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                SmallQuantityButton("−", false, onMinus)
                Box(Modifier.width(29.dp).height(32.dp).border(1.dp, Line, RoundedCornerShape(9.dp)), contentAlignment = Alignment.Center) {
                    Text(quantity.toString(), fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
                SmallQuantityButton("+", true, onPlus)
            }
            Text(rupees(product.price * quantity), fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.End, modifier = Modifier.widthIn(min = 52.dp))
        }
    } else {
        Row(Modifier.fillMaxWidth().heightIn(min = 56.dp).padding(vertical = 7.dp), verticalAlignment = Alignment.CenterVertically) {
            Text(product.name, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 2, modifier = Modifier.weight(1.3f))
            Text(rupees(product.price), fontSize = 13.sp, color = Muted, textAlign = TextAlign.End, modifier = Modifier.weight(.75f))
            Row(Modifier.weight(1.65f), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                SmallQuantityButton("−", false, onMinus)
                Box(Modifier.padding(horizontal = 3.dp).width(35.dp).height(34.dp).border(1.dp, Line, RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) {
                    Text(quantity.toString(), fontWeight = FontWeight.Bold, fontSize = 15.sp)
                }
                SmallQuantityButton("+", true, onPlus)
            }
            Text(rupees(product.price * quantity), fontSize = 14.sp, fontWeight = FontWeight.ExtraBold, textAlign = TextAlign.End, modifier = Modifier.weight(.9f))
        }
    }
}

@Composable
private fun SmallQuantityButton(label: String, plus: Boolean, onClick: () -> Unit) {
    Surface(onClick = onClick, shape = CircleShape, color = if (plus) Yellow else Color(0xFFE5E7EB), modifier = Modifier.size(32.dp)) {
        Box(contentAlignment = Alignment.Center) { Text(label, fontSize = 22.sp, fontWeight = FontWeight.Bold, color = Ink) }
    }
}

@Composable
private fun MenuScreen(
    products: List<Product>, category: String, onCategory: (String) -> Unit, onAdd: () -> Unit,
    onEdit: (Product) -> Unit, onToggle: (Product, Boolean) -> Unit, onDelete: (Product) -> Unit
) {
    val categories = listOf("All", "Vindaloo", "Roast", "Fry")
    val filtered = if (category == "All") products else products.filter { it.category.equals(category, true) }
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
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                categories.forEach { CategoryChip(it, category == it) { onCategory(it) } }
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
                        Text(rupees(product.price), color = Red, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold)
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
                Text("Total Items: ${products.size}", fontWeight = FontWeight.Bold)
                Text("Active: ${products.count { it.active }}", color = Green, fontWeight = FontWeight.Bold)
            }
            Spacer(Modifier.height(20.dp))
        }
    }
}

@Composable
private fun AddItemScreen(product: Product?, onCancel: () -> Unit, onSave: (Product) -> Unit) {
    val context = LocalContext.current
    var name by remember { mutableStateOf(product?.name ?: "") }
    var category by remember { mutableStateOf(product?.category ?: "Vindaloo") }
    var price by remember { mutableStateOf(product?.price?.toString() ?: "") }
    var description by remember { mutableStateOf(product?.description ?: "") }
    var active by remember { mutableStateOf(product?.active ?: true) }
    var imageRef by remember { mutableStateOf(product?.imageRef ?: "") }
    var categoryExpanded by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }
    val pickImage = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) {
            try {
                val folder = File(context.filesDir, "product_images").apply { mkdirs() }
                val destination = File(folder, "item_${System.currentTimeMillis()}.jpg")
                context.contentResolver.openInputStream(uri)?.use { input -> destination.outputStream().use { output -> input.copyTo(output) } }
                if (destination.length() > 2L * 1024L * 1024L) {
                    destination.delete()
                    Toast.makeText(context, "Please choose an image smaller than 2 MB", Toast.LENGTH_LONG).show()
                } else if (destination.length() > 0L) {
                    imageRef = destination.absolutePath
                } else {
                    destination.delete()
                    Toast.makeText(context, "Could not read the selected image", Toast.LENGTH_SHORT).show()
                }
            } catch (_: Exception) {
                Toast.makeText(context, "Unable to load selected image", Toast.LENGTH_SHORT).show()
            }
        }
    }
    val imageBitmap = remember(imageRef) { if (imageRef.startsWith("/") && File(imageRef).exists()) BitmapFactory.decodeFile(imageRef) else null }

    Column(Modifier.fillMaxSize().imePadding().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Row(Modifier.fillMaxWidth().clickable { pickImage.launch("image/*") }.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                if (imageBitmap != null) Image(imageBitmap.asImageBitmap(), null, Modifier.size(104.dp).clip(RoundedCornerShape(14.dp)), contentScale = ContentScale.Crop)
                else if (imageRef.isNotBlank() && imageRef in listOf("pork_vindaloo", "pork_roast", "pork_fry")) {
                    ProductImage(product ?: Product(name = name, category = category, price = 0, imageRef = imageRef), Modifier.size(104.dp).clip(RoundedCornerShape(14.dp)))
                } else Box(Modifier.size(104.dp).clip(RoundedCornerShape(14.dp)).background(Color(0xFFF0F2F4)), contentAlignment = Alignment.Center) {
                    Icon(Icons.Filled.CameraAlt, null, tint = Muted, modifier = Modifier.size(36.dp))
                }
                Spacer(Modifier.width(15.dp))
                Column(Modifier.weight(1f)) {
                    Text("Item Image", fontSize = 17.sp, fontWeight = FontWeight.Bold)
                    Text("JPG, PNG (Max 2 MB)", fontSize = 13.sp, color = Muted)
                    Text("Tap to choose image", fontSize = 12.sp, color = Red, fontWeight = FontWeight.SemiBold)
                }
                Icon(Icons.Filled.Image, null, tint = Muted)
            }
        }
        FormLabel("Item Name *")
        OutlinedTextField(name, { name = it; error = "" }, Modifier.fillMaxWidth(), placeholder = { Text("e.g. Pork Vindaloo") }, singleLine = true, shape = RoundedCornerShape(13.dp))
        FormLabel("Category *")
        Box {
            OutlinedButton(onClick = { categoryExpanded = true }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(13.dp), border = BorderStroke(1.dp, Line)) {
                Text(category, modifier = Modifier.weight(1f), textAlign = TextAlign.Start, color = Ink)
                Text("⌄", fontSize = 22.sp, color = Ink)
            }
            DropdownMenu(expanded = categoryExpanded, onDismissRequest = { categoryExpanded = false }) {
                listOf("Vindaloo", "Roast", "Fry", "Other").forEach { option ->
                    DropdownMenuItem(text = { Text(option) }, onClick = { category = option; categoryExpanded = false })
                }
            }
        }
        FormLabel("Price (₹) *")
        OutlinedTextField(price, { price = it.filter(Char::isDigit).take(7); error = "" }, Modifier.fillMaxWidth(), placeholder = { Text("e.g. 240") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true, shape = RoundedCornerShape(13.dp))
        FormLabel("Description (Optional)")
        OutlinedTextField(description, { description = it }, Modifier.fillMaxWidth(), minLines = 3, shape = RoundedCornerShape(13.dp), placeholder = { Text("Add a short description") })
        Text("Item Status", fontWeight = FontWeight.Bold, fontSize = 16.sp)
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(checked = active, onCheckedChange = { active = it }, colors = androidx.compose.material3.SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = Green, checkedBorderColor = Green))
            Spacer(Modifier.width(8.dp)); Text(if (active) "Active (Visible in POS)" else "Inactive (Hidden from POS)", color = Muted)
        }
        if (error.isNotBlank()) Text(error, color = Red, fontSize = 13.sp)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f).height(54.dp), shape = RoundedCornerShape(13.dp)) { Text("Cancel", fontWeight = FontWeight.Bold) }
            Button(
                onClick = {
                    val parsed = price.toIntOrNull()
                    if (name.isBlank()) error = "Enter an item name"
                    else if (parsed == null || parsed <= 0) error = "Enter a valid price"
                    else onSave(Product(id = product?.id ?: 0L, name = name, category = category, price = parsed, description = description, active = active, imageRef = imageRef))
                }, modifier = Modifier.weight(1.35f).height(54.dp), colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink), shape = RoundedCornerShape(13.dp)
            ) {
                Icon(Icons.Filled.Check, null); Spacer(Modifier.width(6.dp)); Text("Save Item", fontWeight = FontWeight.ExtraBold)
            }
        }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun FormLabel(text: String) { Text(text, fontSize = 15.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(start = 2.dp)) }

@Composable
private fun BillsScreen(bills: List<Bill>, onOpen: (Bill) -> Unit, onShare: (Bill) -> Unit) {
    if (bills.isEmpty()) {
        EmptyState("No bills yet", "Completed purchases will appear here")
        return
    }
    LazyColumn(Modifier.fillMaxSize().padding(12.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
        item { Text("Saved Bills", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, modifier = Modifier.padding(vertical = 4.dp)) }
        items(bills, key = { it.id }) { bill ->
            Card(shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
                Row(Modifier.fillMaxWidth().clickable { onOpen(bill) }.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(46.dp).clip(RoundedCornerShape(12.dp)).background(Cream), contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.ReceiptLong, null, tint = Red, modifier = Modifier.size(25.dp))
                    }
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text(bill.billNo, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                        Text(bill.customerName, color = Muted, fontSize = 13.sp)
                        Text(formatDate(bill.createdAt), color = Muted, fontSize = 11.sp)
                    }
                    Column(horizontalAlignment = Alignment.End) {
                        Text(rupees(bill.total), color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                        IconButton(onClick = { onShare(bill) }, modifier = Modifier.size(34.dp)) { Icon(Icons.Filled.Share, "Share bill", tint = Green) }
                    }
                }
            }
        }
    }
}

@Composable
private fun BillDetailsScreen(bill: Bill, settings: BusinessSettings, onShare: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(20.dp)) {
            Column(Modifier.fillMaxWidth().padding(18.dp)) {
                Text(settings.businessName, fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
                Text("BILL / INVOICE", color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                Divider(Modifier.padding(vertical = 12.dp))
                DetailLine("Bill No", bill.billNo)
                DetailLine("Date", formatDate(bill.createdAt))
                DetailLine("Customer", bill.customerName)
                DetailLine("Mobile", bill.mobile)
                Divider(Modifier.padding(vertical = 12.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Item", fontWeight = FontWeight.Bold); Text("Qty", fontWeight = FontWeight.Bold); Text("Price", fontWeight = FontWeight.Bold); Text("Amount", fontWeight = FontWeight.Bold)
                }
                bill.items.forEach { line ->
                    Divider(color = Line, modifier = Modifier.padding(vertical = 8.dp))
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(line.productName, modifier = Modifier.weight(1.4f), fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                        Text(line.quantity.toString(), modifier = Modifier.weight(.45f), textAlign = TextAlign.Center, fontSize = 13.sp)
                        Text(rupees(line.unitPrice), modifier = Modifier.weight(.7f), textAlign = TextAlign.End, fontSize = 13.sp)
                        Text(rupees(line.amount), modifier = Modifier.weight(.8f), textAlign = TextAlign.End, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    }
                }
                Divider(Modifier.padding(vertical = 10.dp))
                Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Cream).padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("Total Amount", fontWeight = FontWeight.ExtraBold, fontSize = 18.sp)
                    Spacer(Modifier.weight(1f)); Text(rupees(bill.total), color = Red, fontWeight = FontWeight.ExtraBold, fontSize = 24.sp)
                }
            }
        }
        Button(onClick = onShare, modifier = Modifier.fillMaxWidth().height(58.dp), colors = ButtonDefaults.buttonColors(containerColor = Green), shape = RoundedCornerShape(15.dp)) {
            Icon(Icons.Filled.Share, null); Spacer(Modifier.width(8.dp)); Text("Share Invoice Image", fontWeight = FontWeight.Bold, fontSize = 17.sp)
        }
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(label, color = Muted, modifier = Modifier.width(100.dp))
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun SalesScreen(db: PosDatabase, bills: List<Bill>) {
    val todayStart = remember { Calendar.getInstance().apply { set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }.timeInMillis }
    val monthStart = remember { Calendar.getInstance().apply { set(Calendar.DAY_OF_MONTH, 1); set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }.timeInMillis }
    val today = db.getSales(todayStart)
    val month = db.getSales(monthStart)
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("Sales Overview", fontSize = 22.sp, fontWeight = FontWeight.ExtraBold)
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("Today's Sales", rupees(today.first), "${today.second} bills", Yellow, Modifier.weight(1f))
            MetricCard("This Month", rupees(month.first), "${month.second} bills", Color(0xFFE8F3EB), Modifier.weight(1f))
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

@Composable
private fun MetricCard(title: String, amount: String, subtitle: String, tint: Color, modifier: Modifier = Modifier) {
    Card(modifier, shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = tint), elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.fillMaxWidth().padding(14.dp)) {
            Text(title, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = Muted)
            Text(amount, fontSize = 23.sp, fontWeight = FontWeight.ExtraBold, color = if (tint == Yellow) Red else Ink, maxLines = 1)
            Text(subtitle, fontSize = 12.sp, color = Muted)
        }
    }
}

@Composable
private fun SettingsScreen(settings: BusinessSettings, onSave: (BusinessSettings) -> Unit) {
    var name by remember(settings) { mutableStateOf(settings.businessName) }
    var contact by remember(settings) { mutableStateOf(settings.contactNumber) }
    var location by remember(settings) { mutableStateOf(settings.location) }
    var tagline by remember(settings) { mutableStateOf(settings.tagline) }
    var prefix by remember(settings) { mutableStateOf(settings.billPrefix) }
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
                OutlinedTextField(contact, { contact = it.filter { c -> c.isDigit() || c == '+' }.take(15) }, Modifier.fillMaxWidth(), keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), singleLine = true, shape = RoundedCornerShape(12.dp))
                FormLabel("Shop Location")
                OutlinedTextField(location, { location = it }, Modifier.fillMaxWidth(), minLines = 2, shape = RoundedCornerShape(12.dp))
                FormLabel("Invoice Tagline")
                OutlinedTextField(tagline, { tagline = it }, Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp))
                FormLabel("Bill Number Prefix")
                OutlinedTextField(prefix, { prefix = it.uppercase(Locale.ENGLISH).filter { c -> c.isLetterOrDigit() }.take(5) }, Modifier.fillMaxWidth(), singleLine = true, shape = RoundedCornerShape(12.dp))
            }
        }
        Card(colors = CardDefaults.cardColors(containerColor = Color.White), shape = RoundedCornerShape(18.dp)) {
            Column(Modifier.padding(15.dp)) {
                Text("WhatsApp Sharing", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                Text("The app generates an invoice PNG and opens WhatsApp Business when it is installed. Choose the customer's chat in WhatsApp to send the image.", fontSize = 13.sp, color = Muted, lineHeight = 19.sp)
            }
        }
        Button(onClick = { onSave(BusinessSettings(name.trim(), contact.trim(), location.trim(), tagline.trim(), prefix.ifBlank { "TP" })) }, modifier = Modifier.fillMaxWidth().height(56.dp), colors = ButtonDefaults.buttonColors(containerColor = Yellow, contentColor = Ink), shape = RoundedCornerShape(14.dp)) {
            Icon(Icons.Filled.Check, null); Spacer(Modifier.width(8.dp)); Text("Save Settings", fontWeight = FontWeight.ExtraBold)
        }
        Spacer(Modifier.height(20.dp))
    }
}

@Composable
private fun EmptyState(title: String, subtitle: String) {
    Column(Modifier.fillMaxWidth().padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
        Icon(Icons.Filled.Restaurant, null, tint = Color(0xFFB5BBC3), modifier = Modifier.size(42.dp))
        Spacer(Modifier.height(8.dp)); Text(title, fontSize = 18.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Muted, textAlign = TextAlign.Center, fontSize = 13.sp)
    }
}

private fun shareInvoiceImage(context: Context, imageFile: File, bill: Bill, settings: BusinessSettings) {
    val uri: Uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", imageFile)
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "image/png"
        putExtra(Intent.EXTRA_STREAM, uri)
        putExtra(Intent.EXTRA_TEXT, "Thank you for ordering from ${settings.businessName}!\nBill: ${bill.billNo}\nTotal: ${rupees(bill.total)}")
        clipData = ClipData.newUri(context.contentResolver, "${bill.billNo} invoice", uri)
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
        context.startActivity(Intent.createChooser(intent, "Share invoice image"))
    }
}

private fun isPackageInstalled(context: Context, packageName: String): Boolean = try {
    @Suppress("DEPRECATION")
    context.packageManager.getPackageInfo(packageName, 0)
    true
} catch (_: Exception) { false }

private fun rupees(value: Int): String = "₹${String.format(Locale.ENGLISH, "%,d", value)}"
private fun formatDate(millis: Long): String = SimpleDateFormat("dd MMM yyyy, hh:mm a", Locale.ENGLISH).format(Date(millis))
