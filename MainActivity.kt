package com.example.niftyaitrader

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.NumberFormat
import java.util.Locale

private val BG = Color(0xFF080D18)
private val PANEL = Color(0xFF121C2E)
private val MUTED = Color(0xFF9AABC7)
private val GREEN = Color(0xFF63D6B0)
private val AMBER = Color(0xFFFFC76B)
private val RED = Color(0xFFFF7777)

data class Position(val id:Int,val symbol:String,val side:String,val qty:Int,val entry:Double,val sl:Double,val target:Double)
data class Trade(val symbol:String,val side:String,val qty:Int,val entry:Double,val exit:Double,val pnl:Double)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) { super.onCreate(savedInstanceState); setContent { App() } }
}

@Composable private fun App() {
    var tab by remember { mutableStateOf("Home") }
    var symbol by remember { mutableStateOf("NIFTY") }
    var side by remember { mutableStateOf("BUY") }
    var qty by remember { mutableStateOf("50") }
    var entry by remember { mutableStateOf("") }
    var sl by remember { mutableStateOf("") }
    var target by remember { mutableStateOf("") }
    var exit by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var nextId by remember { mutableIntStateOf(1) }
    val positions = remember { mutableStateListOf<Position>() }
    val history = remember { mutableStateListOf<Trade>() }
    val money = remember { NumberFormat.getCurrencyInstance(Locale("en","IN")) }
    val used by remember { derivedStateOf { positions.sumOf { it.entry * it.qty } } }
    val free by remember { derivedStateOf { 500000.0 - used } }

    MaterialTheme(colorScheme = darkColorScheme(background=BG, surface=PANEL, primary=GREEN, onBackground=Color.White, onSurface=Color.White)) {
        Scaffold(containerColor=BG, bottomBar={
            NavigationBar(containerColor=PANEL) {
                listOf("Home","Signals","Paper","Positions","History").forEach { t ->
                    NavigationBarItem(selected=tab==t,onClick={tab=t;note=""},icon={Text(when(t){"Home"->"⌂";"Signals"->"⌁";"Paper"->"＋";"Positions"->"▣";else->"◷"},fontSize=18.sp)},label={Text(t,fontSize=10.sp)},
                        colors=NavigationBarItemDefaults.colors(selectedIconColor=GREEN,selectedTextColor=GREEN,indicatorColor=Color(0xFF19263B),unselectedTextColor=MUTED))
                }
            }
        }) { pad ->
            Column(Modifier.fillMaxSize().padding(pad)) {
                Column(Modifier.padding(horizontal=18.dp,vertical=12.dp)) {
                    Text("NIFTY AI TRADER PRO",fontSize=22.sp,fontWeight=FontWeight.Bold)
                    Text("ANGEL ONE • NOT CONNECTED  |  PAPER MODE",color=AMBER,fontSize=11.sp)
                }
                when(tab) {
                    "Home" -> Home(positions.size,history.size,free,money)
                    "Signals" -> Signals()
                    "Paper" -> Paper(symbol,{symbol=it.uppercase()},side,{side=it},qty,{qty=it},entry,{entry=it},sl,{sl=it},target,{target=it},free,money,note,{
                        val q=qty.toIntOrNull(); val e=entry.toDoubleOrNull(); val s=sl.toDoubleOrNull(); val tg=target.toDoubleOrNull()
                        note=when {
                            symbol.isBlank() -> "Symbol enter karein."
                            q==null||q<=0 -> "Quantity positive honi chahiye."
                            e==null||e<=0 -> "Valid assumed entry price enter karein."
                            s==null||tg==null||s<=0||tg<=0 -> "Stop-loss aur target enter karein."
                            side=="BUY" && !(s<e && tg>e) -> "BUY ke liye SL entry se neeche aur target upar hona chahiye."
                            side=="SELL" && !(s>e && tg<e) -> "SELL ke liye SL entry se upar aur target neeche hona chahiye."
                            e*q>free -> "Virtual balance kam hai."
                            else -> { positions.add(Position(nextId++,symbol.trim().uppercase(),side,q,e,s,tg)); entry="";sl="";target="";"Virtual order record hua; broker ko kuch nahi bheja gaya." }
                        }
                    })
                    "Positions" -> OpenPositions(positions,exit,{exit=it},money,note,{p->
                        val x=exit.toDoubleOrNull()
                        if(x==null||x<=0) note="Valid assumed exit price enter karein."
                        else { val pnl=if(p.side=="BUY")(x-p.entry)*p.qty else (p.entry-x)*p.qty
                            history.add(0,Trade(p.symbol,p.side,p.qty,p.entry,x,pnl));positions.remove(p);exit="";note="Virtual position close ho gayi." }
                    })
                    else -> History(history,money)
                }
            }
        }
    }
}

@Composable private fun Home(open:Int,closed:Int,free:Double,money:NumberFormat) {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){ Metric("VIRTUAL CAPITAL","₹5,00,000","Simulation only",Modifier.weight(1f));Metric("AVAILABLE",money.format(free),"Paper ledger",Modifier.weight(1f)) } }
        item { PanelCard { Text("MARKET CONNECTION",color=MUTED,fontSize=12.sp);Text("Not connected",fontSize=21.sp);Text("Angel One feed is not configured. No live prices are displayed.",color=MUTED,fontSize=13.sp);Pill("LIVE DATA OFF",AMBER) } }
        item { PanelCard { Text("TRADING MODE",color=MUTED,fontSize=12.sp);Text("PAPER TRADING ONLY",color=GREEN,fontSize=20.sp,fontWeight=FontWeight.Bold);Text("Virtual ledger only. No real broker orders or real-money execution.",color=MUTED,fontSize=13.sp) } }
        item { Row(horizontalArrangement=Arrangement.spacedBy(10.dp)){Metric("OPEN POSITIONS",open.toString(),"Virtual trades",Modifier.weight(1f));Metric("CLOSED TRADES",closed.toString(),"History",Modifier.weight(1f))} }
        item { PanelCard { Text("WATCHLIST — LIVE PRICES NOT CONNECTED",fontWeight=FontWeight.Bold);Watch("NIFTY 50","Awaiting verified feed");Watch("BANK NIFTY","Awaiting verified feed");Watch("FINNIFTY","Awaiting verified feed") } }
        item { PanelCard { Text("INDICATORS",fontWeight=FontWeight.Bold);Text("EMA • RSI • VWAP",color=GREEN);Text("Values unavailable until verified market data is connected.",color=MUTED,fontSize=12.sp) } }
    }
}
@Composable private fun Signals() {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { PanelCard { Text("AI SIGNAL ENGINE",fontSize=18.sp,fontWeight=FontWeight.Bold);Pill("WAITING FOR MARKET DATA",AMBER);Text("BUY/SELL signals are disabled until a verified data source is connected. No fabricated calls.",color=MUTED,fontSize=13.sp) } }
        item { PanelCard { Watch("Trend","EMA unavailable");Watch("Momentum","RSI unavailable");Watch("VWAP","Unavailable");Watch("Confidence","Not calculated") } }
    }
}
@Composable private fun Paper(symbol:String,onSymbol:(String)->Unit,side:String,onSide:(String)->Unit,qty:String,onQty:(String)->Unit,entry:String,onEntry:(String)->Unit,sl:String,onSl:(String)->Unit,target:String,onTarget:(String)->Unit,free:Double,money:NumberFormat,note:String,onPlace:()->Unit) {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        item { PanelCard {
            Text("NEW PAPER TRADE",fontSize=18.sp,fontWeight=FontWeight.Bold)
            Text("Available virtual balance: ${money.format(free)}",color=MUTED,fontSize=12.sp)
            Field("Symbol",symbol,onSymbol,false)
            Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){FilterChip(side=="BUY",{onSide("BUY")},label={Text("BUY / LONG")});FilterChip(side=="SELL",{onSide("SELL")},label={Text("SELL / SHORT")})}
            Field("Quantity",qty,onQty,true);Field("Assumed entry price (₹)",entry,onEntry,true);Field("Stop-loss (₹)",sl,onSl,true);Field("Target (₹)",target,onTarget,true)
            Button(onClick=onPlace,modifier=Modifier.fillMaxWidth()){Text("PLACE VIRTUAL ORDER")}
            if(note.isNotBlank()) Text(note,color=GREEN,fontSize=12.sp)
            Text("Manual assumed price only; this is not a live quote.",color=AMBER,fontSize=11.sp)
        } }
    }
}
@Composable private fun OpenPositions(items:List<Position>,exit:String,onExit:(String)->Unit,money:NumberFormat,note:String,onClose:(Position)->Unit) {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        item { Text("OPEN PAPER POSITIONS",fontSize=18.sp,fontWeight=FontWeight.Bold) }
        if(items.isEmpty()) item { PanelCard { Text("No open positions");Text("Create a virtual trade from the Paper tab.",color=MUTED,fontSize=13.sp) } }
        items(items,key={it.id}) { p -> PanelCard {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text(p.symbol,fontWeight=FontWeight.Bold,fontSize=18.sp);Pill(p.side,if(p.side=="BUY")GREEN else AMBER)}
            Text("Qty ${p.qty} • Entry ${money.format(p.entry)}",color=MUTED,fontSize=12.sp)
            Text("SL ${money.format(p.sl)} • Target ${money.format(p.target)}",color=MUTED,fontSize=12.sp)
            Field("Assumed exit price (₹)",exit,onExit,true)
            Button(onClick={onClose(p)},modifier=Modifier.fillMaxWidth()){Text("CLOSE PAPER POSITION")}
        } }
        if(note.isNotBlank()) item { Text(note,color=GREEN,fontSize=12.sp) }
    }
}
@Composable private fun History(items:List<Trade>,money:NumberFormat) {
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
        item { Text("PAPER TRADE HISTORY",fontSize=18.sp,fontWeight=FontWeight.Bold) }
        if(items.isEmpty()) item { PanelCard { Text("No closed trades yet");Text("Closed virtual trades appear here.",color=MUTED,fontSize=13.sp) } }
        items(items) { t -> PanelCard {
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("${t.symbol} • ${t.side}",fontWeight=FontWeight.Bold);Text(money.format(t.pnl),color=if(t.pnl>=0)GREEN else RED,fontWeight=FontWeight.Bold)}
            Text("Qty ${t.qty} | Entry ${money.format(t.entry)} | Exit ${money.format(t.exit)}",color=MUTED,fontSize=12.sp)
        } }
    }
}
@Composable private fun Metric(title:String,value:String,foot:String,modifier:Modifier=Modifier) {
    Card(modifier,colors=CardDefaults.cardColors(containerColor=PANEL),shape=RoundedCornerShape(16.dp)){Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(5.dp)){Text(title,color=MUTED,fontSize=10.sp,fontWeight=FontWeight.Bold);Text(value,fontSize=17.sp,fontWeight=FontWeight.Bold);Text(foot,color=MUTED,fontSize=10.sp)}}
}
@Composable private fun PanelCard(content:@Composable ColumnScope.()->Unit) {
    Card(colors=CardDefaults.cardColors(containerColor=PANEL),shape=RoundedCornerShape(16.dp)){Column(Modifier.fillMaxWidth().padding(16.dp),verticalArrangement=Arrangement.spacedBy(10.dp),content=content)}
}
@Composable private fun Pill(text:String,color:Color) { Surface(color=color.copy(alpha=.14f),shape=RoundedCornerShape(50)){Text(text,color=color,fontSize=10.sp,fontWeight=FontWeight.Bold,modifier=Modifier.padding(horizontal=10.dp,vertical=6.dp))} }
@Composable private fun Watch(name:String,value:String) { Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Text(name,fontSize=13.sp,fontWeight=FontWeight.Medium);Text(value,color=MUTED,fontSize=11.sp)} }
@Composable private fun Field(label:String,value:String,onValue:(String)->Unit,numeric:Boolean) {
    OutlinedTextField(value,onValue,label={Text(label)},singleLine=true,keyboardOptions=KeyboardOptions(keyboardType=if(numeric)KeyboardType.Decimal else KeyboardType.Text),modifier=Modifier.fillMaxWidth())
}
