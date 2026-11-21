package com.trivandrumpork.pos

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import org.json.JSONArray
import org.json.JSONObject
import java.net.URLEncoder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

data class Food(val name: String, val category: String, val price: Int, val active: Boolean = true)
data class BillLine(val name: String, val qty: Int, val price: Int)
data class Bill(val id: Int, val customer: String, val phone: String, val total: Int, val time: String, val lines: List<BillLine>)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { PosApp() }
    }
}

@Composable
fun PosApp() {
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("takeaway_pos", 0) }
    val defaults = listOf(
        Food("Pork Vindaloo", "Vindaloo", 240), Food("Pork Roast", "Roast", 200),
        Food("Pork Varattu (Fry)", "Fry", 200), Food("Pork Pepper Fry", "Fry", 220),
        Food("Pork Chilli", "Fry", 230), Food("Pork Biryani", "Other", 280),
        Food("Pork Cutlet (2 pcs)", "Other", 120)
    )
    fun loadMenu(): List<Food> {
        val raw = prefs.getString("menu", null) ?: return defaults
        return try { val a=JSONArray(raw); (0 until a.length()).map { val o=a.getJSONObject(it); Food(o.getString("name"),o.getString("category"),o.getInt("price"),o.optBoolean("active",true)) } } catch (_:Exception) { defaults }
    }
    fun saveMenu(list: List<Food>) {
        val a=JSONArray(); list.forEach { a.put(JSONObject().put("name",it.name).put("category",it.category).put("price",it.price).put("active",it.active)) }
        prefs.edit().putString("menu",a.toString()).apply()
    }
    fun loadBills(): List<Bill> {
        val raw=prefs.getString("bills","[]") ?: "[]"
        return try { val a=JSONArray(raw); (0 until a.length()).map { val o=a.getJSONObject(it); val l=o.getJSONArray("lines"); Bill(o.getInt("id"),o.getString("customer"),o.getString("phone"),o.getInt("total"),o.getString("time"),(0 until l.length()).map { j -> val x=l.getJSONObject(j); BillLine(x.getString("name"),x.getInt("qty"),x.getInt("price")) }) }.reversed() } catch (_:Exception) { emptyList() }
    }
    var menu by remember { mutableStateOf(loadMenu()) }
    var cart by remember { mutableStateOf(mapOf<String,Int>()) }
    var customer by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var tab by remember { mutableStateOf("POS") }
    var category by remember { mutableStateOf("All") }
    var bills by remember { mutableStateOf(loadBills()) }
    var showAdd by remember { mutableStateOf(false) }
    var newName by remember { mutableStateOf("") }
    var newCategory by remember { mutableStateOf("Other") }
    var newPrice by remember { mutableStateOf("") }
    val activeMenu = menu.filter { it.active }
    val total = cart.entries.sumOf { (name,qty) -> (menu.find { it.name==name }?.price ?: 0)*qty }
    val purple = Color(0xFF6818C7)
    val red = Color(0xFFB5121B)
    val green = Color(0xFF079B38)

    MaterialTheme(colorScheme = lightColorScheme(primary=purple, secondary=red)) {
        Scaffold(containerColor=Color(0xFFF7F6FA), topBar={
            TopAppBarCompat(title=tab, subtitle="TRIVANDRUM PORK", purple=purple)
        }, bottomBar={
            NavigationBar {
                listOf("POS","Bills","Menu","Reports").forEach { label ->
                    NavigationBarItem(selected=tab==label,onClick={tab=label},icon={ Icon(when(label){"POS"->Icons.Default.ShoppingCart;"Bills"->Icons.Default.Receipt;"Menu"->Icons.Default.Restaurant;else->Icons.Default.BarChart},null) },label={Text(label)})
                }
            }
        }) { padding ->
            Column(Modifier.fillMaxSize().padding(padding).padding(horizontal=12.dp)) {
                when(tab) {
                    "POS" -> {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                            StatCard("Today's Orders", "${bills.size}", Modifier.weight(1f))
                            StatCard("Today's Sales", "₹${bills.sumOf { it.total }}", Modifier.weight(1f))
                        }
                        Spacer(Modifier.height(10.dp))
                        Row(horizontalArrangement=Arrangement.spacedBy(6.dp)) {
                            listOf("All","Vindaloo","Roast","Fry","Other").forEach { FilterChip(selected=category==it,onClick={category=it},label={Text(it)}) }
                        }
                        LazyVerticalGrid(columns=GridCells.Fixed(2),modifier=Modifier.weight(1f),horizontalArrangement=Arrangement.spacedBy(8.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                            items(activeMenu.filter { category=="All" || it.category==category }) { food ->
                                Card(shape=RoundedCornerShape(16.dp), colors=CardDefaults.cardColors(containerColor=Color.White)) {
                                    Column(Modifier.padding(12.dp)) {
                                        Text(food.name,fontWeight=FontWeight.Bold,minLines=2)
                                        Text("₹${food.price}",color=red,fontSize=19.sp,fontWeight=FontWeight.Bold)
                                        Button(onClick={cart=cart+(food.name to ((cart[food.name]?:0)+1))},modifier=Modifier.fillMaxWidth()) { Text("+ Add") }
                                    }
                                }
                            }
                        }
                        if(cart.isNotEmpty()) {
                            Card(Modifier.fillMaxWidth().padding(vertical=8.dp),colors=CardDefaults.cardColors(containerColor=Color.White)) {
                                Column(Modifier.padding(12.dp)) {
                                    Text("Current Order (${cart.values.sum()} items)",fontWeight=FontWeight.Bold)
                                    cart.forEach { (name,qty) ->
                                        val price=menu.find { it.name==name }?.price ?: 0
                                        Row(Modifier.fillMaxWidth().padding(vertical=3.dp),verticalAlignment=Alignment.CenterVertically) {
                                            Text(name,Modifier.weight(1f),fontSize=13.sp)
                                            TextButton(onClick={val n=qty-1; cart=if(n<=0) cart-name else cart+(name to n)}) { Text("−") }
                                            Text("$qty")
                                            TextButton(onClick={cart=cart+(name to (qty+1))}) { Text("+") }
                                            Text("₹${qty*price}",fontWeight=FontWeight.SemiBold)
                                        }
                                    }
                                    HorizontalDivider()
                                    Text("Grand Total  ₹$total",fontSize=20.sp,fontWeight=FontWeight.Bold,color=purple)
                                    OutlinedTextField(customer,{customer=it},label={Text("Customer name")},modifier=Modifier.fillMaxWidth(),singleLine=true)
                                    OutlinedTextField(phone,{phone=it.filter { c -> c.isDigit() }.takeLast(10)},label={Text("WhatsApp number (10 digits)")},modifier=Modifier.fillMaxWidth(),singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone))
                                    Button(onClick={
                                        if(customer.isBlank() || phone.length!=10 || cart.isEmpty()) return@Button
                                        val id=(prefs.getInt("last_id",0)+1)
                                        val lines=cart.map { (n,q)-> BillLine(n,q,menu.find { it.name==n }?.price?:0) }
                                        val time=SimpleDateFormat("dd MMM yyyy, hh:mm a",Locale.getDefault()).format(Date())
                                        val bill=Bill(id,customer.trim(),phone,total,time,lines)
                                        val all=JSONArray(prefs.getString("bills","[]"))
                                        val la=JSONArray(); lines.forEach { la.put(JSONObject().put("name",it.name).put("qty",it.qty).put("price",it.price)) }
                                        all.put(JSONObject().put("id",id).put("customer",bill.customer).put("phone",bill.phone).put("total",bill.total).put("time",time).put("lines",la))
                                        prefs.edit().putString("bills",all.toString()).putInt("last_id",id).apply()
                                        bills=loadBills()
                                        val itemText=lines.joinToString("\n") { "${it.name} x ${it.qty} - ₹${it.price*it.qty}" }
                                        val message="Hello ${bill.customer}, your takeaway order #TP${id.toString().padStart(4,'0')} is ready.\nItems:\n$itemText\nTotal: ₹${bill.total}. Thank you for choosing Trivandrum Pork!"
                                        val url="https://wa.me/91${bill.phone}?text="+URLEncoder.encode(message,"UTF-8")
                                        context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(url)))
                                        cart=emptyMap(); customer=""; phone=""
                                    },modifier=Modifier.fillMaxWidth(),colors=ButtonDefaults.buttonColors(containerColor=green)) { Text("Save & Send to WhatsApp",fontWeight=FontWeight.Bold) }
                                }
                            }
                        }
                    }
                    "Bills" -> LazyColumn { items(bills) { b -> Card(Modifier.fillMaxWidth().padding(vertical=4.dp),colors=CardDefaults.cardColors(containerColor=Color.White)) { Column(Modifier.padding(14.dp)) { Text("TP${b.id.toString().padStart(4,'0')}  •  ${b.time}",fontWeight=FontWeight.Bold); Text(b.customer); Text("₹${b.total}",color=purple,fontWeight=FontWeight.Bold); b.lines.forEach { Text("${it.name} × ${it.qty}") } } } } }
                    "Menu" -> {
                        Row(verticalAlignment=Alignment.CenterVertically) { Text("Menu Manager",Modifier.weight(1f),fontWeight=FontWeight.Bold,fontSize=20.sp); Button(onClick={showAdd=true}) { Text("+ Add item") } }
                        LazyColumn { items(menu) { f -> Card(Modifier.fillMaxWidth().padding(vertical=4.dp),colors=CardDefaults.cardColors(containerColor=Color.White)) { Row(Modifier.padding(12.dp),verticalAlignment=Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(f.name,fontWeight=FontWeight.Bold); Text("${f.category} • ₹${f.price}") }; Switch(f.active,{v->menu=menu.map { if(it.name==f.name) it.copy(active=v) else it };saveMenu(menu)}) } } } }
                    }
                    else -> {
                        Text("Sales Summary",fontWeight=FontWeight.Bold,fontSize=22.sp)
                        StatCard("Total bills",bills.size.toString(),Modifier.fillMaxWidth())
                        StatCard("Total sales","₹${bills.sumOf { it.total }}",Modifier.fillMaxWidth())
                    }
                }
            }
        }
        if(showAdd) AlertDialog(onDismissRequest={showAdd=false},title={Text("Add menu item")},text={
            Column { OutlinedTextField(newName,{newName=it},label={Text("Item name")}); OutlinedTextField(newCategory,{newCategory=it},label={Text("Category")}); OutlinedTextField(newPrice,{newPrice=it},label={Text("Price ₹")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number)) }
        },confirmButton={ TextButton(onClick={val p=newPrice.toIntOrNull(); if(newName.isNotBlank() && p!=null && p>0){menu=menu+Food(newName.trim(),newCategory.trim(),p);saveMenu(menu);newName="";newPrice="";showAdd=false}}){Text("Save")} },dismissButton={TextButton(onClick={showAdd=false}){Text("Cancel")}})
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TopAppBarCompat(title:String, subtitle:String, purple:Color) {
    CenterAlignedTopAppBar(title={Column(horizontalAlignment=Alignment.CenterHorizontally){Text(subtitle,fontSize=11.sp,color=purple,fontWeight=FontWeight.Bold);Text(title,fontWeight=FontWeight.Bold)}},colors=TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor=Color.White))
}
@Composable
fun StatCard(title:String,value:String,modifier:Modifier=Modifier) {
    Card(modifier.padding(vertical=4.dp),colors=CardDefaults.cardColors(containerColor=Color.White)) { Column(Modifier.padding(12.dp)) { Text(title,fontSize=12.sp,color=Color.Gray); Text(value,fontSize=20.sp,fontWeight=FontWeight.Bold,color=Color(0xFF5415A7)) } }
}
