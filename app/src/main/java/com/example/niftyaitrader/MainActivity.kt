package com.example.niftyaitrader

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Canvas
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
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.background
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import java.text.NumberFormat
import java.util.Locale
import java.net.HttpURLConnection
import java.net.URL

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
    val context = LocalContext.current
    val prefs = remember { context.getSharedPreferences("paper_ledger", Context.MODE_PRIVATE) }
    var tab by remember { mutableStateOf("Home") }
    var closeInput by remember { mutableStateOf("") }
    var csvRaw by remember { mutableStateOf("") }
    var csvFileName by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    val csvPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
                    ?: error("File could not be opened")
            }.onSuccess { content ->
                val parsed = parseMarketCsv(content)
                if (parsed.error != null) {
                    csvRaw = ""
                    csvFileName = ""
                    note = "CSV import: ${parsed.error}"
                } else {
                    csvRaw = content
                    csvFileName = uri.lastPathSegment?.substringAfterLast('/') ?: "Imported CSV"
                    closeInput = parsed.closes.joinToString(", ") { it.toString() }
                    note = "CSV imported: ${parsed.closes.size} valid closing rows. Historical data only."
                }
            }.onFailure { note = "CSV import failed: ${it.message ?: "unknown error"}" }
        }
    }
    var symbol by remember { mutableStateOf("NIFTY") }
    var side by remember { mutableStateOf("BUY") }
    var qty by remember { mutableStateOf("50") }
    var entry by remember { mutableStateOf("") }
    var sl by remember { mutableStateOf("") }
    var target by remember { mutableStateOf("") }
    var exit by remember { mutableStateOf("") }
    val positions = remember { mutableStateListOf<Position>().apply {
        val saved = runCatching { JSONArray(prefs.getString("positions", "[]")) }.getOrNull()
        if (saved != null) for (i in 0 until saved.length()) runCatching {
            val o = saved.getJSONObject(i)
            add(Position(o.getInt("id"),o.getString("symbol"),o.getString("side"),o.getInt("qty"),o.getDouble("entry"),o.getDouble("sl"),o.getDouble("target")))
        }
    } }
    var nextId by remember { mutableIntStateOf((positions.maxOfOrNull { it.id } ?: 0) + 1) }
    val history = remember { mutableStateListOf<Trade>().apply {
        val saved = runCatching { JSONArray(prefs.getString("history", "[]")) }.getOrNull()
        if (saved != null) for (i in 0 until saved.length()) runCatching {
            val o = saved.getJSONObject(i)
            add(Trade(o.getString("symbol"),o.getString("side"),o.getInt("qty"),o.getDouble("entry"),o.getDouble("exit"),o.getDouble("pnl")))
        }
    } }
    LaunchedEffect(positions.size, history.size) {
        val posJson = JSONArray().apply { positions.forEach { p -> put(JSONObject().put("id",p.id).put("symbol",p.symbol).put("side",p.side).put("qty",p.qty).put("entry",p.entry).put("sl",p.sl).put("target",p.target)) } }
        val histJson = JSONArray().apply { history.forEach { t -> put(JSONObject().put("symbol",t.symbol).put("side",t.side).put("qty",t.qty).put("entry",t.entry).put("exit",t.exit).put("pnl",t.pnl)) } }
        prefs.edit().putString("positions",posJson.toString()).putString("history",histJson.toString()).apply()
    }
    val money = remember { NumberFormat.getCurrencyInstance(Locale("en","IN")) }
    val used by remember { derivedStateOf { positions.sumOf { it.entry * it.qty } } }
    val free by remember { derivedStateOf { 500000.0 - used } }

    MaterialTheme(colorScheme = darkColorScheme(background=BG, surface=PANEL, primary=GREEN, onBackground=Color.White, onSurface=Color.White)) {
        Scaffold(containerColor=BG, bottomBar={
            NavigationBar(containerColor=PANEL) {
                listOf("Home","Analysis","Momentum","Integration","Paper","Positions","History").forEach { t ->
                    NavigationBarItem(selected=tab==t,onClick={tab=t;note=""},icon={Text(when(t){"Home"->"⌂";"Analysis"->"⌁";"Momentum"->"↗";"Integration"->"⇄";"Paper"->"＋";"Positions"->"▣";else->"◷"},fontSize=18.sp)},label={Text(t,fontSize=10.sp)},
                        colors=NavigationBarItemDefaults.colors(selectedIconColor=GREEN,selectedTextColor=GREEN,indicatorColor=Color(0xFF19263B),unselectedTextColor=MUTED))
                }
            }
        }) { pad ->
            Column(Modifier.fillMaxSize().padding(pad)) {
                Column(Modifier.padding(horizontal=18.dp,vertical=12.dp)) {
                    Text("NIFTY AI TRADER PRO",fontSize=22.sp,fontWeight=FontWeight.Bold)
                    Text("NO LIVE FEED • PAPER MODE ONLY",color=AMBER,fontSize=11.sp)
                }
                when(tab) {
                    "Home" -> Home(positions.size,history.size,free,money)
                    "Analysis" -> Signals(closeInput,{closeInput=it},csvRaw,csvFileName,{ csvPicker.launch(arrayOf("text/*", "application/vnd.ms-excel", "application/csv")) },{ closeInput=""; csvRaw=""; csvFileName=""; note="CSV and manual input cleared." })
                    "Momentum" -> MomentumScreen(prefs, BuildConfig.API_BASE_URL, csvRaw, csvFileName)
                    "Integration" -> IntegrationStatus(prefs, BuildConfig.API_BASE_URL)
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




@Composable private fun MomentumScreen(prefs: android.content.SharedPreferences, defaultApiBaseUrl: String, importedCsv: String, importedCsvName: String) {
    var apiBaseUrl by remember {
        mutableStateOf(prefs.getString("api_base_url", defaultApiBaseUrl).orEmpty().trim().trimEnd('/'))
    }
    var requestJson by remember { mutableStateOf("") }
    var responseText by remember { mutableStateOf("Analysis request abhi nahi bheji gayi.") }
    var requestStatus by remember { mutableStateOf("READY") }
    var busy by remember { mutableStateOf(false) }
    var marketSnapshot by remember { mutableStateOf("No market snapshot fetched yet.") }
    var marketFetchStatus by remember { mutableStateOf("NOT CHECKED") }
    var marketFetching by remember { mutableStateOf(false) }
    var simulationFetching by remember { mutableStateOf(false) }
    var historicalFetching by remember { mutableStateOf(false) }
    var simulatedResult by remember { mutableStateOf("No simulated snapshot requested yet.") }
    var historicalResult by remember { mutableStateOf("No synthetic historical analysis requested yet.") }
    var historicalStatus by remember { mutableStateOf("NOT RUN") }
    var historicalAnalysisJson by remember { mutableStateOf("") }
    var historicalCandlesJson by remember { mutableStateOf("") }
    var multiFactorJson by remember { mutableStateOf("") }
    var walkForwardJson by remember { mutableStateOf("") }
    var datasetValidationJson by remember { mutableStateOf("") }
    var researchStatus by remember { mutableStateOf("NOT RUN") }
    var chartWindow by remember { mutableIntStateOf(80) }
    var requestSectionExpanded by remember { mutableStateOf(false) }
    var engineResponseExpanded by remember { mutableStateOf(false) }
    var csvResearchBusy by remember { mutableStateOf(false) }
    var csvResearchStatus by remember { mutableStateOf("NO CSV RESEARCH RUN") }
    var csvResearchResult by remember { mutableStateOf("") }
    var replayBusy by remember { mutableStateOf(false) }
    var replayId by remember { mutableStateOf("") }
    var replayStatus by remember { mutableStateOf("NOT STARTED") }
    var replayResult by remember { mutableStateOf("No historical replay started.") }

    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item {
            PanelCard {
                Text("MULTI-FACTOR RESEARCH ENGINE",fontSize=17.sp,fontWeight=FontWeight.Bold)
                Pill("PAPER RESEARCH • READ-ONLY",AMBER)
                Text("Completed historical OHLCV candles ka transparent multi-factor context. Yeh prediction, live feed ya BUY/SELL instruction nahi hai.",color=MUTED,fontSize=12.sp)
                StatusRow("Backend URL",if(apiBaseUrl.isBlank()) "NOT SET" else "CONFIGURED")
                StatusRow("Analysis","Multi-factor + historical research")
                StatusRow("Request",requestStatus)
            }
        }
        item {
            PanelCard {
                Text("IMPORTED HISTORICAL CSV RESEARCH",fontSize=15.sp,fontWeight=FontWeight.Bold)
                Pill("USER-SUPPLIED DATA • READ-ONLY",AMBER)
                StatusRow("Selected file", if(importedCsvName.isBlank()) "NO CSV IMPORTED" else importedCsvName)
                StatusRow("Pipeline status", csvResearchStatus)
                Text("The CSV imported in Analysis is sent to the backend for OHLC/OHLCV validation, multi-factor context and chronological walk-forward research. Source authenticity is not independently verified.",color=MUTED,fontSize=12.sp)
                Button(
                    onClick={
                        if(csvResearchBusy || apiBaseUrl.isBlank() || importedCsv.isBlank()) return@Button
                        csvResearchBusy = true
                        csvResearchStatus = "RUNNING"
                        csvResearchResult = "Submitting imported historical CSV for validation and research…"
                        Thread {
                            var bodyText = "Research request failed."
                            var state = "REQUEST FAILED"
                            try {
                                val connection = (URL("$apiBaseUrl/api/research/historical-csv").openConnection() as HttpURLConnection)
                                connection.requestMethod = "POST"
                                connection.connectTimeout = 15000
                                connection.readTimeout = 45000
                                connection.doOutput = true
                                connection.setRequestProperty("Content-Type", "text/csv; charset=utf-8")
                                connection.setRequestProperty("Accept", "application/json")
                                connection.outputStream.use { it.write(importedCsv.toByteArray(Charsets.UTF_8)) }
                                val code = connection.responseCode
                                val stream = if(code in 200..299) connection.inputStream else connection.errorStream
                                val raw = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                if(code in 200..299) {
                                    val root = JSONObject(raw)
                                    val validation = root.optJSONObject("dataset_validation")
                                    val factors = root.optJSONObject("multi_factor")
                                    val walk = root.optJSONObject("walk_forward")
                                    val accuracyText = if (walk == null || walk.isNull("directional_accuracy_pct")) "Unavailable" else "${walk.optDouble("directional_accuracy_pct")}%"
                                    bodyText = """HISTORICAL CSV RESEARCH COMPLETE
Rows: ${root.optInt("rows")}
Source authenticity: ${root.optString("source_authenticity")}
Dataset valid: ${validation?.optBoolean("valid")}
Gap check: ${if (validation == null || validation.isNull("interval_seconds_checked")) "NOT RUN (interval not supplied)" else validation.optInt("gap_count").toString()}
Factor agreement: ${factors?.optString("factor_agreement")}
Context score: ${factors?.optInt("directional_context_score")}
Walk-forward observations: ${walk?.optInt("out_of_sample_predictions")}
Directional accuracy: $accuracyText
No trade signal or real orders are generated.

Full response: $raw"""
                                    state = "RESEARCH COMPLETE • SOURCE UNVERIFIED"
                                } else {
                                    bodyText = "HTTP $code\n$raw"
                                    state = "HTTP $code"
                                }
                                connection.disconnect()
                            } catch(e:Exception) {
                                bodyText = e.message ?: "Network error"
                            }
                            Handler(Looper.getMainLooper()).post {
                                csvResearchResult = bodyText
                                csvResearchStatus = state
                                csvResearchBusy = false
                            }
                        }.start()
                    },
                    enabled = !csvResearchBusy && apiBaseUrl.isNotBlank() && importedCsv.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) { Text(if(csvResearchBusy) "RESEARCH RUNNING…" else "ANALYSE IMPORTED HISTORICAL CSV") }
                Button(
                    onClick={
                        if(replayBusy || apiBaseUrl.isBlank() || importedCsv.isBlank()) return@Button
                        replayBusy=true
                        replayStatus="STARTING"
                        Thread {
                            var result="Historical replay request failed."
                            var state="REQUEST FAILED"
                            var newId=""
                            try {
                                val connection=(URL("$apiBaseUrl/api/replay/historical-csv?interval_ms=250").openConnection() as HttpURLConnection)
                                connection.requestMethod="POST"
                                connection.connectTimeout=15000
                                connection.readTimeout=45000
                                connection.doOutput=true
                                connection.setRequestProperty("Content-Type","text/csv; charset=utf-8")
                                connection.setRequestProperty("Accept","application/json")
                                connection.outputStream.use { it.write(importedCsv.toByteArray(Charsets.UTF_8)) }
                                val code=connection.responseCode
                                val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                                val raw=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                if(code in 200..299) {
                                    val root=JSONObject(raw)
                                    newId=root.optString("replay_id")
                                    result="Historical replay started.\nRows: ${root.optInt("total")}\nClassification: ${root.optString("classification")}\nReplay ID: $newId\nEvents are labelled HISTORICAL_CSV_REPLAY and DELAYED; they are not live prices."
                                    state="RUNNING • HISTORICAL ONLY"
                                } else {
                                    result="HTTP $code\n$raw"
                                    state="HTTP $code"
                                }
                                connection.disconnect()
                            } catch(e:Exception) { result=e.message ?: "Network error" }
                            Handler(Looper.getMainLooper()).post {
                                replayId=newId
                                replayResult=result
                                replayStatus=state
                                replayBusy=false
                            }
                        }.start()
                    },
                    enabled=!replayBusy && apiBaseUrl.isNotBlank() && importedCsv.isNotBlank(),
                    modifier=Modifier.fillMaxWidth()
                ) { Text(if(replayBusy) "STARTING REPLAY…" else "START HISTORICAL CSV REPLAY") }
                StatusRow("Replay status",replayStatus)
                if(replayResult.isNotBlank()) Text(replayResult,color=if(replayStatus.startsWith("RUNNING")) AMBER else MUTED,fontSize=11.sp)
                if(replayId.isNotBlank()) Button(
                    onClick={
                        Thread {
                            var result="Replay status unavailable."
                            var state="REQUEST FAILED"
                            try {
                                val connection=(URL("$apiBaseUrl/api/replay/$replayId").openConnection() as HttpURLConnection)
                                connection.requestMethod="GET"
                                connection.connectTimeout=10000
                                connection.readTimeout=10000
                                val code=connection.responseCode
                                val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                                val raw=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                if(code in 200..299) {
                                    val root=JSONObject(raw)
                                    state=root.optString("status","UNKNOWN")
                                    result="Status: $state\nPublished: ${root.optInt("published")}/${root.optInt("total")}\nSource: ${root.optString("source")}\nHistorical replay only; not live data."
                                } else result="HTTP $code\n$raw"
                                connection.disconnect()
                            } catch(e:Exception) { result=e.message ?: "Network error" }
                            Handler(Looper.getMainLooper()).post { replayStatus=state; replayResult=result }
                        }.start()
                    }, modifier=Modifier.fillMaxWidth()
                ) { Text("REFRESH REPLAY STATUS") }
                if(csvResearchResult.isNotBlank()) Text(csvResearchResult,color=if(csvResearchStatus.startsWith("RESEARCH COMPLETE")) GREEN else MUTED,fontSize=11.sp)
                Text("Minimum 50 valid OHLCV rows. Date-only daily rows are normalized to UTC midnight for ordering; timezone-naive intraday timestamps are rejected. No missing bars are invented.",color=AMBER,fontSize=11.sp)
            }
        }
        item {
            PanelCard {
                HistoricalOhlcChart(importedCsv)
            }
        }
        item {
            PanelCard {
                Text("LATEST VERIFIED MARKET EVENT",fontSize=15.sp,fontWeight=FontWeight.Bold)
                Pill("READ-ONLY • NO SYNTHETIC PRICE",AMBER)
                StatusRow("Endpoint","/api/market/latest?symbol=NIFTY")
                StatusRow("Fetch status",marketFetchStatus)
                Text(marketSnapshot,color=MUTED,fontSize=12.sp)
                Button(
                    onClick={
                        if (marketFetching || apiBaseUrl.isBlank()) return@Button
                        marketFetching=true
                        marketFetchStatus="FETCHING"
                        Thread {
                            var result="Market snapshot unavailable."
                            var status="REQUEST FAILED"
                            try {
                                val connection=(URL("$apiBaseUrl/api/market/latest?symbol=NIFTY").openConnection() as HttpURLConnection)
                                connection.requestMethod="GET"
                                connection.connectTimeout=10000
                                connection.readTimeout=15000
                                connection.setRequestProperty("Accept","application/json")
                                val code=connection.responseCode
                                val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                                val raw=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                if(code in 200..299) {
                                    val root=JSONObject(raw)
                                    val events=root.optJSONObject("events")
                                    val event=events?.optJSONObject("NIFTY")
                                    result=if(event==null) {
                                        "NO VERIFIED EVENT CACHED. Backend reports ${root.optString("status","UNKNOWN")}. No price will be estimated or fabricated."
                                    } else {
                                        "NIFTY: ${event.optDouble("last_price")}\nSource: ${event.optString("source")}\nFreshness: ${event.optString("freshness")}\nExchange time: ${event.optString("exchange_timestamp")}\nRead-only: ${event.optBoolean("read_only")}"
                                    }
                                    status=if(event==null) "NO EVENT" else event.optString("freshness","AVAILABLE")
                                } else {
                                    result="HTTP $code\n$raw"
                                    status="HTTP $code"
                                }
                                connection.disconnect()
                            } catch(e:Exception) {
                                result=e.message ?: "Network error"
                            }
                            Handler(Looper.getMainLooper()).post {
                                marketSnapshot=result
                                marketFetchStatus=status
                                marketFetching=false
                            }
                        }.start()
                    },
                    enabled=!marketFetching && apiBaseUrl.isNotBlank(),
                    modifier=Modifier.fillMaxWidth()
                ) { Text(if(marketFetching) "FETCHING…" else "REFRESH MARKET SNAPSHOT") }
                Text("A snapshot is not proof of a continuously running feed. Confirm source and freshness before using it for research.",color=AMBER,fontSize=11.sp)
            }
        }
        item {
            PanelCard {
                Text("SIMULATED MARKET FEED",fontSize=15.sp,fontWeight=FontWeight.Bold)
                Pill("SYNTHETIC DATA • PAPER ONLY",AMBER)
                Text("This generates a clearly labelled test price. It is not a live NIFTY quote and must not be used for real trading decisions.",color=MUTED,fontSize=12.sp)
                Button(onClick={
                    if(simulationFetching || apiBaseUrl.isBlank()) return@Button
                    simulationFetching=true
                    marketFetchStatus="GENERATING SIMULATION"
                    simulatedResult="Request sent to backend. Waiting for response…"
                    Thread {
                        var result="Simulation unavailable."; var state="REQUEST FAILED"
                        try {
                            val connection=(URL("$apiBaseUrl/api/simulation/snapshot").openConnection() as HttpURLConnection)
                            connection.requestMethod="GET"; connection.connectTimeout=10000; connection.readTimeout=15000
                            val code=connection.responseCode
                            val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                            val raw=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                            if(code in 200..299) {
                                val obj=JSONObject(raw)
                                result="SIMULATED NIFTY: ${obj.optDouble("last_price")}\nSource: ${obj.optString("source")}\nClassification: ${obj.optString("data_type")}\nNo broker orders are possible."
                                state="SIMULATED ONLY"
                            } else { result="HTTP $code\n$raw"; state="HTTP $code" }
                            connection.disconnect()
                        } catch(e:Exception) { result=e.message ?: "Network error" }
                        Handler(Looper.getMainLooper()).post {
                            marketSnapshot=result
                            marketFetchStatus=state
                            simulatedResult="$state\n$result"
                            simulationFetching=false
                        }
                    }.start()
                },enabled=!simulationFetching && apiBaseUrl.isNotBlank(),modifier=Modifier.fillMaxWidth()) { Text(if(simulationFetching) "REQUEST IN PROGRESS…" else "GENERATE SIMULATED SNAPSHOT") }
                Text(simulatedResult,color=if(simulatedResult.startsWith("SIMULATED ONLY")) GREEN else MUTED,fontSize=12.sp)
                Button(onClick={
                    if(simulationFetching || apiBaseUrl.isBlank()) return@Button
                    simulationFetching=true
                    historicalStatus="LOADING"
                    historicalResult="Request sent to backend. Waiting for historical sample and analysis…"
                    Thread {
                        var result="Historical sample unavailable."; var state="REQUEST FAILED"; var analysisJson=""; var candlesJson=""
                        try {
                            val connection=(URL("$apiBaseUrl/api/simulation/historical-sample?count=80").openConnection() as HttpURLConnection)
                            connection.requestMethod="GET"; connection.connectTimeout=10000; connection.readTimeout=15000
                            val code=connection.responseCode
                            val stream=if(code in 200..299) connection.inputStream else connection.errorStream
                            val raw=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                            if(code in 200..299) {
                                val obj=JSONObject(raw); val candles=obj.getJSONArray("candles"); candlesJson=candles.toString()
                                val highs=org.json.JSONArray(); val lows=org.json.JSONArray(); val closes=org.json.JSONArray(); val volumes=org.json.JSONArray()
                                for(i in 0 until candles.length()) { val c=candles.getJSONObject(i); highs.put(c.getDouble("high")); lows.put(c.getDouble("low")); closes.put(c.getDouble("close")); volumes.put(c.getDouble("volume")) }
                                val payload=JSONObject().put("high",highs).put("low",lows).put("close",closes).put("volume",volumes)
                                val analysis=(URL("$apiBaseUrl/api/analysis/market-context").openConnection() as HttpURLConnection)
                                analysis.requestMethod="POST"; analysis.connectTimeout=10000; analysis.readTimeout=20000; analysis.doOutput=true
                                analysis.setRequestProperty("Content-Type","application/json")
                                analysis.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
                                val aCode=analysis.responseCode; val aStream=if(aCode in 200..299) analysis.inputStream else analysis.errorStream
                                val aRaw=aStream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                if (aCode in 200..299) {
                                    analysisJson = aRaw
                                    val multiPayload = JSONObject(payload.toString())
                                    val (multiCode, multiRaw) = postJson("$apiBaseUrl/api/analysis/multi-factor", multiPayload)
                                    if (multiCode in 200..299) multiFactorJson = multiRaw
                                    val datasetRows = JSONArray()
                                    for (j in 0 until candles.length()) {
                                        val c = candles.getJSONObject(j)
                                        datasetRows.put(JSONObject()
                                            .put("timestamp", c.getString("date"))
                                            .put("open", c.getDouble("open"))
                                            .put("high", c.getDouble("high"))
                                            .put("low", c.getDouble("low"))
                                            .put("close", c.getDouble("close"))
                                            .put("volume", c.getDouble("volume")))
                                    }
                                    val (validationCode, validationRaw) = postJson(
                                        "$apiBaseUrl/api/analysis/validate-dataset",
                                        JSONObject().put("rows", datasetRows).put("interval_seconds", 300)
                                    )
                                    if (validationCode in 200..299) datasetValidationJson = validationRaw
                                    val (walkCode, walkRaw) = postJson(
                                        "$apiBaseUrl/api/research/walk-forward",
                                        JSONObject().put("close_prices", closes).put("min_history", 30)
                                    )
                                    if (walkCode in 200..299) walkForwardJson = walkRaw
                                    val allOk = multiCode in 200..299 && validationCode in 200..299 && walkCode in 200..299
                                    researchStatus = if (allOk) "ALL RESEARCH CHECKS PASSED" else
                                        "PARTIAL: multi=$multiCode validation=$validationCode walk=$walkCode"
                                    result="SYNTHETIC SAMPLE • ${candles.length()} candles\nMarket context HTTP $aCode; multi-factor HTTP $multiCode; data validation HTTP $validationCode; walk-forward HTTP $walkCode.\nSynthetic sample only; not exchange history."
                                } else {
                                    result="SYNTHETIC HISTORICAL SAMPLE • ${candles.length()} candles\nAnalysis HTTP $aCode\n$aRaw"
                                    researchStatus = "MARKET CONTEXT HTTP $aCode"
                                }
                                state=if(aCode in 200..299) "SYNTHETIC HISTORY ANALYSED" else "ANALYSIS HTTP $aCode"
                                analysis.disconnect()
                            } else { result="HTTP $code\n$raw"; state="HTTP $code" }
                            connection.disconnect()
                        } catch(e:Exception) { result=e.message ?: "Network error" }
                        Handler(Looper.getMainLooper()).post {
                            responseText=result
                            requestStatus=state
                            historicalStatus=state
                            historicalAnalysisJson=analysisJson
                            historicalCandlesJson=candlesJson
                            historicalResult="$state\n$result"
                            simulationFetching=false
                        }
                    }.start()
                },enabled=!simulationFetching && apiBaseUrl.isNotBlank(),modifier=Modifier.fillMaxWidth()) { Text(if(simulationFetching) "REQUEST IN PROGRESS…" else "ANALYSE SYNTHETIC HISTORICAL SAMPLE") }
                StatusRow("Historical test status",historicalStatus)
                Text(historicalResult,color=if(historicalStatus=="SYNTHETIC HISTORY ANALYSED") GREEN else MUTED,fontSize=12.sp)
                if (historicalAnalysisJson.isNotBlank()) {
                    HistoricalIndicatorCards(historicalAnalysisJson)
                    if (historicalCandlesJson.isNotBlank()) SyntheticMarketCharts(historicalCandlesJson, historicalAnalysisJson, chartWindow, { chartWindow = it })
                    PanelCard {
                        Text("V6.0 MULTI-FACTOR & RESEARCH",fontSize=15.sp,fontWeight=FontWeight.Bold)
                        Pill("HISTORICAL RESEARCH • PAPER ONLY",AMBER)
                        StatusRow("Research pipeline",researchStatus)
                        if (multiFactorJson.isNotBlank()) MultiFactorSummary(multiFactorJson)
                        if (datasetValidationJson.isNotBlank()) DatasetValidationSummary(datasetValidationJson)
                        if (walkForwardJson.isNotBlank()) WalkForwardSummary(walkForwardJson)
                        Text("This panel uses synthetic sample candles for integration testing. Its metrics are not evidence of real-market accuracy or future performance.",color=AMBER,fontSize=11.sp)
                    }
                }
            }
        }
        item {
            PanelCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween, verticalAlignment=Alignment.CenterVertically) {
                    Text("REQUEST JSON",fontWeight=FontWeight.Bold)
                    TextButton(onClick={ requestSectionExpanded = !requestSectionExpanded }) { Text(if(requestSectionExpanded) "HIDE ▲" else "SHOW ▼", color=GREEN) }
                }
                if (requestSectionExpanded) {
                OutlinedTextField(
                    value=requestJson,onValueChange={requestJson=it},
                    modifier=Modifier.fillMaxWidth().heightIn(min=220.dp),
                    label={Text("Paste completed candle JSON")},
                    placeholder={Text("""{"high":[...],"low":[...],"close":[...],"volume":[...]}""")},
                    minLines=8,
                    colors=OutlinedTextFieldDefaults.colors(
                        focusedTextColor=Color.White,unfocusedTextColor=Color.White,
                        focusedBorderColor=GREEN,unfocusedBorderColor=MUTED,
                        focusedLabelColor=GREEN,unfocusedLabelColor=MUTED,cursorColor=GREEN
                    )
                )
                Text("Kam se kam 50 aligned completed OHLC candles dein. Arrays high, low, close aur optional volume hon. Synthetic data sirf integration testing ke liye hai. API keys ya credentials paste na karein.",color=AMBER,fontSize=11.sp)
                Button(
                    onClick={
                        if(busy || apiBaseUrl.isBlank()) return@Button
                        val validJson=runCatching { JSONObject(requestJson) }.isSuccess
                        if(!validJson) {
                            requestStatus="INVALID JSON"
                            responseText="JSON format sahi nahi hai. Request send nahi hui."
                        } else {
                            busy=true
                            requestStatus="SENDING"
                            Thread {
                                var bodyText=""
                                var state="REQUEST FAILED"
                                try {
                                    val connection=(URL("$apiBaseUrl/api/analysis/multi-factor").openConnection() as HttpURLConnection)
                                    connection.requestMethod="POST"
                                    connection.connectTimeout=15000
                                    connection.readTimeout=25000
                                    connection.doOutput=true
                                    connection.setRequestProperty("Content-Type","application/json; charset=utf-8")
                                    connection.setRequestProperty("Accept","application/json")
                                    connection.outputStream.use { it.write(requestJson.toByteArray(Charsets.UTF_8)) }
                                    val httpCode=connection.responseCode
                                    val stream=if(httpCode in 200..299) connection.inputStream else connection.errorStream
                                    val response=stream?.bufferedReader()?.use { it.readText() }.orEmpty()
                                    bodyText="HTTP $httpCode\n$response"
                                    state=if(httpCode in 200..299) "RESPONSE RECEIVED" else "HTTP $httpCode"
                                    connection.disconnect()
                                } catch(e:Exception) {
                                    bodyText=e.message ?: "Network error"
                                }
                                Handler(Looper.getMainLooper()).post {
                                    responseText=bodyText
                                    requestStatus=state
                                    busy=false
                                }
                            }.start()
                        }
                    },
                    enabled=!busy && apiBaseUrl.isNotBlank() && requestJson.isNotBlank(),
                    modifier=Modifier.fillMaxWidth()
                ) { Text(if(busy) "ANALYSING…" else "RUN PAPER ANALYSIS") }
                OutlinedButton(
                    onClick={requestJson="";responseText="Analysis request abhi nahi bheji gayi.";requestStatus="READY"},
                    enabled=!busy,modifier=Modifier.fillMaxWidth()
                ) { Text("CLEAR") }
                }
            }
        }
        item {
            PanelCard {
                Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween, verticalAlignment=Alignment.CenterVertically) {
                    Text("ENGINE RESPONSE",fontWeight=FontWeight.Bold)
                    TextButton(onClick={ engineResponseExpanded = !engineResponseExpanded }) { Text(if(engineResponseExpanded) "HIDE ▲" else "SHOW ▼", color=GREEN) }
                }
                if (engineResponseExpanded) Text(responseText,color=MUTED,fontSize=11.sp)
            }
        }
        item {
            PanelCard {
                Text("DATA STATUS",fontWeight=FontWeight.Bold)
                StatusRow("Live data verified","NO")
                StatusRow("Real orders","DISABLED")
                Text("Yeh user-supplied/historical data ka paper analysis hai. Backend supplied values ya provider freshness ko independently verify nahi karta. Missing inputs ko assume nahi kiya jata.",color=AMBER,fontSize=11.sp)
            }
        }
    }
}

@Composable private fun IntegrationStatus(prefs: android.content.SharedPreferences, defaultApiBaseUrl: String) {
    var apiBaseUrl by remember { mutableStateOf(prefs.getString("api_base_url", defaultApiBaseUrl).orEmpty()) }
    var urlDraft by remember { mutableStateOf(apiBaseUrl) }
    var saveMessage by remember { mutableStateOf("") }
    var checkState by remember { mutableStateOf(if (apiBaseUrl.isBlank()) "BACKEND URL NOT SET" else "NOT CHECKED") }
    var detail by remember { mutableStateOf("Enter your deployed HTTPS backend URL, then save it.") }
    var checking by remember { mutableStateOf(false) }
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item {
            PanelCard {
                Text("PROVIDER INTEGRATION STATUS",fontSize=17.sp,fontWeight=FontWeight.Bold)
                Pill("FOUNDATION ONLY • NOT LIVE",AMBER)
                Text("This page checks the deployed backend health endpoint. It does not authenticate a broker or enable market orders.",color=MUTED,fontSize=13.sp)
            }
        }
        item {
            PanelCard {
                Text("BACKEND CONNECTIVITY",fontWeight=FontWeight.Bold)
                StatusRow("Configured API URL",if(apiBaseUrl.isBlank()) "NOT SET" else "SET")
                OutlinedTextField(
                    value=urlDraft,
                    onValueChange={ urlDraft=it.trim() },
                    modifier=Modifier.fillMaxWidth(),
                    singleLine=true,
                    label={ Text("Backend HTTPS URL") },
                    placeholder={ Text("https://your-service.onrender.com") },
                    keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Uri),
                    colors=OutlinedTextFieldDefaults.colors(
                        focusedTextColor=Color.White, unfocusedTextColor=Color.White,
                        focusedBorderColor=GREEN, unfocusedBorderColor=MUTED,
                        focusedLabelColor=GREEN, unfocusedLabelColor=MUTED,
                        cursorColor=GREEN
                    )
                )
                Button(onClick={
                    val candidate=urlDraft.trim().trimEnd('/')
                    val valid=runCatching { val parsed=URL(candidate); parsed.protocol=="https" && !parsed.host.isNullOrBlank() }.getOrDefault(false)
                    if (!valid) { saveMessage="Valid HTTPS URL enter karein (https://...onrender.com)." }
                    else {
                        apiBaseUrl=candidate
                        prefs.edit().putString("api_base_url",candidate).apply()
                        checkState="NOT CHECKED"
                        detail="Backend URL saved on this device. Connection ab check kar sakte hain."
                        saveMessage="URL saved on this device."
                    }
                },modifier=Modifier.fillMaxWidth()) { Text("SAVE BACKEND URL") }
                if(saveMessage.isNotBlank()) Text(saveMessage,color=if(saveMessage.startsWith("URL saved")) GREEN else AMBER,fontSize=12.sp)
                StatusRow("Connection check",checkState)
                Text(detail,color=MUTED,fontSize=12.sp)
                Button(onClick={
                    if (apiBaseUrl.isBlank() || checking) return@Button
                    checking=true; checkState="CHECKING"; detail="Contacting HTTPS backend health endpoint…"
                    Thread {
                        var result="CONNECTION FAILED"; var info="Could not reach backend. Verify deployment and URL."
                        try {
                            val conn=(URL(apiBaseUrl.trimEnd('/')+"/api/v5/integration-status").openConnection() as HttpURLConnection)
                            conn.requestMethod="GET"; conn.connectTimeout=8000; conn.readTimeout=8000
                            val code=conn.responseCode
                            if(code in 200..299) { result="BACKEND REACHABLE"; info="HTTP $code — integration status received. Provider/live feed status must still be checked separately." }
                            else { result="HTTP $code"; info="Backend responded but returned HTTP $code." }
                            conn.disconnect()
                        } catch (e: Exception) { info=(e.message ?: "Network error").take(160) }
                        Handler(Looper.getMainLooper()).post {
                            checkState=result
                            detail=info
                            checking=false
                        }
                    }.start()
                },enabled=apiBaseUrl.isNotBlank() && !checking,modifier=Modifier.fillMaxWidth()) { Text(if(checking) "CHECKING…" else "CHECK BACKEND CONNECTION") }
                Text("Endpoint: /api/v5/integration-status",color=GREEN,fontSize=11.sp)
            }
        }
        item {
            PanelCard {
                Text("ANGEL ONE SMARTAPI",fontWeight=FontWeight.Bold)
                StatusRow("Adapter interface","PRESENT")
                StatusRow("Account authentication","NOT CONFIGURED")
                StatusRow("Market data stream","NOT CONNECTED")
                StatusRow("Last market event","NONE")
            }
        }
        item {
            PanelCard {
                Text("STREAM & DATA VALIDATION",fontWeight=FontWeight.Bold)
                StatusRow("WebSocket endpoint","BACKEND FOUNDATION")
                StatusRow("Event validation","AVAILABLE IN BACKEND")
                StatusRow("Freshness monitor","CONTRACT READY")
                StatusRow("Live data verified","NO")
            }
        }
        item {
            PanelCard {
                Text("NEWS & SENTIMENT",fontWeight=FontWeight.Bold)
                StatusRow("Provider interface","PRESENT")
                StatusRow("Authorized source","NOT CONFIGURED")
                StatusRow("Latest news timestamp","NONE")
            }
        }
        item {
            PanelCard {
                Text("SAFETY & MODE",fontWeight=FontWeight.Bold)
                StatusRow("App mode","PAPER / EDUCATIONAL")
                StatusRow("Broker order execution","DISABLED")
                StatusRow("Live feed label","OFF")
            }
        }
    }
}


private data class OhlcvPoint(val open: Double, val high: Double, val low: Double, val close: Double, val volume: Double)

private fun emaSeries(values: List<Double>, period: Int): List<Double> {
    if (values.isEmpty()) return emptyList()
    val alpha = 2.0 / (period + 1.0)
    val result = ArrayList<Double>(values.size)
    var previous = values.first()
    values.forEachIndexed { index, value ->
        previous = if (index == 0) value else alpha * value + (1.0 - alpha) * previous
        result.add(previous)
    }
    return result
}

private fun postJson(url: String, payload: JSONObject): Pair<Int, String> {
    val connection = (URL(url).openConnection() as HttpURLConnection)
    return try {
        connection.requestMethod = "POST"
        connection.connectTimeout = 12000
        connection.readTimeout = 25000
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        connection.setRequestProperty("Accept", "application/json")
        connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        code to (stream?.bufferedReader()?.use { it.readText() }.orEmpty())
    } finally {
        connection.disconnect()
    }
}

@Composable private fun MultiFactorSummary(raw: String) {
    val obj = remember(raw) { runCatching { JSONObject(raw) }.getOrNull() }
    if (obj == null) { Text("Multi-factor response could not be parsed.", color=RED); return }
    Text("Factor agreement: ${obj.optString("factor_agreement","UNKNOWN")}",color=GREEN,fontWeight=FontWeight.Bold)
    StatusRow("Context score","${obj.optInt("directional_context_score")} / -2 to +2")
    val factors = obj.optJSONArray("factors") ?: JSONArray()
    for (i in 0 until factors.length()) {
        val f = factors.optJSONObject(i) ?: continue
        StatusRow(f.optString("factor"),f.optString("state"))
    }
    StatusRow("Classification",obj.optString("classification"))
}

@Composable private fun DatasetValidationSummary(raw: String) {
    val obj = remember(raw) { runCatching { JSONObject(raw) }.getOrNull() }
    if (obj == null) { Text("Dataset validation response could not be parsed.",color=RED); return }
    StatusRow("Dataset structure",if(obj.optBoolean("valid")) "VALID" else "INVALID")
    StatusRow("Rows / gaps","${obj.optInt("rows")} / ${obj.optInt("gap_count")}")
    StatusRow("Source authenticity",obj.optString("source_authenticity","NOT VERIFIED"))
}

@Composable private fun WalkForwardSummary(raw: String) {
    val obj = remember(raw) { runCatching { JSONObject(raw) }.getOrNull() }
    if (obj == null) { Text("Walk-forward response could not be parsed.",color=RED); return }
    StatusRow("Out-of-sample observations",obj.optInt("out_of_sample_predictions").toString())
    val accuracy = if (obj.isNull("directional_accuracy_pct")) "N/A" else "${obj.optDouble("directional_accuracy_pct")}%"
    StatusRow("Historical directional accuracy",accuracy)
    StatusRow("Evaluation coverage","${obj.optDouble("coverage_pct")}%")
}

private data class HistoricalBar(val date: String, val open: Double, val high: Double, val low: Double, val close: Double)

@Composable private fun HistoricalOhlcChart(csvText: String) {
    val bars = remember(csvText) {
        runCatching {
            val lines = csvText.removePrefix("\uFEFF").lines().filter { it.isNotBlank() }
            val headerAt = lines.indexOfFirst { line ->
                val h = line.split(",").map { it.trim().trim('"').lowercase().replace(Regex("[^a-z0-9]"), "") }.toSet()
                h.any { it in setOf("date", "indexdate", "tradedate") } &&
                    h.any { it in setOf("open", "openindexvalue", "openprice") } &&
                    h.any { it in setOf("high", "highindexvalue", "highprice") } &&
                    h.any { it in setOf("low", "lowindexvalue", "lowprice") } &&
                    h.any { it in setOf("close", "closingindexvalue", "closeindexvalue", "closingprice") }
            }
            if (headerAt < 0) emptyList() else {
                val headers = lines[headerAt].split(",").map { it.trim().trim('"').lowercase().replace(Regex("[^a-z0-9]"), "") }
                fun col(names: Set<String>) = headers.indexOfFirst { it in names }
                val di=col(setOf("date","indexdate","tradedate"))
                val oi=col(setOf("open","openindexvalue","openprice"))
                val hi=col(setOf("high","highindexvalue","highprice"))
                val li=col(setOf("low","lowindexvalue","lowprice"))
                val ci=col(setOf("close","closingindexvalue","closeindexvalue","closingprice"))
                lines.drop(headerAt+1).mapNotNull { line ->
                    val p=line.split(",").map { it.trim().trim('"').replace(",","") }
                    if (listOf(di,oi,hi,li,ci).any { it<0 || it>=p.size }) null else {
                        val o=p[oi].toDoubleOrNull(); val h=p[hi].toDoubleOrNull()
                        val l=p[li].toDoubleOrNull(); val c=p[ci].toDoubleOrNull()
                        if (o==null || h==null || l==null || c==null || l>minOf(o,c) || h<maxOf(o,c)) null
                        else HistoricalBar(p[di],o,h,l,c)
                    }
                }.takeLast(120)
            }
        }.getOrDefault(emptyList())
    }
    Text("HISTORICAL NIFTY OHLC CHART",fontWeight=FontWeight.Bold,fontSize=15.sp)
    Pill("USER-SUPPLIED HISTORICAL DATA • NOT LIVE",AMBER)
    if (bars.isEmpty()) {
        Text("Import a supported NSE OHLC CSV in Analysis to display its historical candles.",color=MUTED,fontSize=12.sp)
        return
    }
    Text("${bars.size} candles • ${bars.first().date} to ${bars.last().date}",color=MUTED,fontSize=11.sp)
    Text("EMA 9 / 21 overlays are calculated from the supplied closing prices. No volume is invented.",color=MUTED,fontSize=11.sp)
    val closes=bars.map { it.close }
    fun ema(period:Int): List<Double> {
        if (closes.isEmpty()) return emptyList()
        val alpha=2.0/(period+1.0)
        val out=ArrayList<Double>(closes.size)
        var value=closes.take(period.coerceAtMost(closes.size)).average()
        for (i in closes.indices) {
            if (i<period-1) out.add(Double.NaN)
            else {
                if (i==period-1) value=closes.take(period).average()
                else value=closes[i]*alpha+value*(1-alpha)
                out.add(value)
            }
        }
        return out
    }
    val e9=ema(9); val e21=ema(21)
    Canvas(Modifier.fillMaxWidth().height(260.dp)) {
        val left=8f; val right=size.width-8f; val top=10f; val bottom=size.height-10f
        val maxP=bars.maxOf { it.high }; val minP=bars.minOf { it.low }
        val range=(maxP-minP).takeIf { it>0.0 } ?: 1.0
        val step=(right-left)/bars.size
        fun y(v:Double)=bottom-(((v-minP)/range).toFloat()*(bottom-top))
        for (i in 0..4) {
            val gy=top+(bottom-top)*i/4f
            drawLine(MUTED.copy(alpha=.22f),Offset(left,gy),Offset(right,gy),1f)
        }
        bars.forEachIndexed { i,b ->
            val x=left+step*(i+.5f); val color=if(b.close>=b.open) GREEN else RED
            drawLine(color,Offset(x,y(b.high)),Offset(x,y(b.low)),1.4f)
            val bt=minOf(y(b.open),y(b.close)); val bb=maxOf(y(b.open),y(b.close))
            drawRect(color,Offset(x-step*.30f,bt),androidx.compose.ui.geometry.Size(step*.60f,(bb-bt).coerceAtLeast(2f)))
        }
        fun line(values:List<Double>, color:Color) {
            for(i in 1 until values.size) if(values[i-1].isFinite() && values[i].isFinite()) {
                val x1=left+step*(i-.5f); val x2=left+step*(i+.5f)
                drawLine(color,Offset(x1,y(values[i-1])),Offset(x2,y(values[i])),2f)
            }
        }
        line(e9,AMBER); line(e21,Color(0xFF7CB7FF))
    }
    Row(horizontalArrangement=Arrangement.spacedBy(14.dp)) {
        Text("● EMA 9",color=AMBER,fontSize=11.sp)
        Text("● EMA 21",color=Color(0xFF7CB7FF),fontSize=11.sp)
        Text("● OHLC candles",color=MUTED,fontSize=11.sp)
    }
}

@Composable private fun SyntheticMarketCharts(candlesJson: String, analysisJson: String, selectedWindow: Int, onWindowChange: (Int) -> Unit) {
    val candles = remember(candlesJson) {
        runCatching {
            val array = JSONArray(candlesJson)
            (0 until array.length()).map { i ->
                val c = array.getJSONObject(i)
                OhlcvPoint(c.optDouble("open"), c.optDouble("high"), c.optDouble("low"),
                    c.optDouble("close"), c.optDouble("volume"))
            }.filter { it.high.isFinite() && it.low.isFinite() && it.close.isFinite() }
        }.getOrDefault(emptyList())
    }
    val analysis = remember(analysisJson) { runCatching { JSONObject(analysisJson) }.getOrNull() }
    if (candles.isEmpty()) return
    val closes = candles.map { it.close }
    val visibleCandles = candles.takeLast(selectedWindow.coerceAtMost(candles.size))
    val ema9 = remember(candlesJson) { emaSeries(closes, 9) }.takeLast(visibleCandles.size)
    val ema21 = remember(candlesJson) { emaSeries(closes, 21) }.takeLast(visibleCandles.size)
    val ema50 = remember(candlesJson) { emaSeries(closes, 50) }.takeLast(visibleCandles.size)
    PanelCard {
        Text("SYNTHETIC CANDLESTICK CHART", fontWeight=FontWeight.Bold)
        Pill("${visibleCandles.size} GENERATED TEST CANDLES • NOT EXCHANGE DATA", AMBER)
        Text("VISIBLE CANDLE WINDOW", color=MUTED, fontSize=10.sp, fontWeight=FontWeight.Bold)
        Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.spacedBy(8.dp)) {
            listOf(20, 40, 80).forEach { count ->
                FilterChip(
                    selected = selectedWindow == count,
                    onClick = { onWindowChange(count) },
                    modifier = Modifier.weight(1f),
                    label = { Text(count.toString(), maxLines = 1, fontSize = 14.sp) }
                )
            }
        }
        Text("${
            visibleCandles.size
        } of ${candles.size} synthetic candles displayed", color=MUTED, fontSize=10.sp)
        Text("OHLC candles with calculated EMA overlays. The chart is for UI and indicator education only.", color=MUTED, fontSize=11.sp)
        Text("PRICE + EMA OVERLAYS", color=MUTED, fontSize=10.sp, fontWeight=FontWeight.Bold)
        Canvas(Modifier.fillMaxWidth().height(290.dp)) {
            val left = 8f; val right = size.width - 8f
            val top = 12f
            val priceBottom = size.height * 0.70f
            val volumeTop = priceBottom + 12f
            val volumeBottom = size.height - 8f
            val maxPrice = visibleCandles.maxOf { it.high }
            val minPrice = visibleCandles.minOf { it.low }
            val range = (maxPrice - minPrice).takeIf { it > 0.0 } ?: 1.0
            val maxVol = visibleCandles.maxOf { it.volume }.coerceAtLeast(1.0)
            val step = (right-left) / visibleCandles.size
            fun y(price: Double) = priceBottom - (((price-minPrice)/range).toFloat() * (priceBottom-top))
            // subtle price grid
            for (i in 0..3) {
                val gy = top + (priceBottom-top) * i / 3f
                drawLine(MUTED.copy(alpha=0.18f), Offset(left,gy), Offset(right,gy), 1f)
            }
            drawLine(MUTED.copy(alpha=0.35f), Offset(left,volumeTop-4f), Offset(right,volumeTop-4f), 1f)
            visibleCandles.forEachIndexed { i, c ->
                val x = left + step * (i + 0.5f)
                val up = c.close >= c.open
                val candleColor = if (up) GREEN else RED
                drawLine(candleColor, Offset(x,y(c.high)), Offset(x,y(c.low)), 1.5f)
                val bodyTop = minOf(y(c.open),y(c.close))
                val bodyBottom = maxOf(y(c.open),y(c.close))
                drawRect(candleColor, topLeft=Offset(x-step*0.28f,bodyTop),
                    size=androidx.compose.ui.geometry.Size(step*0.56f,(bodyBottom-bodyTop).coerceAtLeast(2f)))
                val volumeHeight = (volumeBottom-volumeTop).coerceAtLeast(1f)
                val vh = ((c.volume/maxVol).toFloat()*volumeHeight)
                drawRect(if(up) GREEN.copy(alpha=0.62f) else RED.copy(alpha=0.62f), topLeft=Offset(x-step*0.30f,volumeBottom-vh),
                    size=androidx.compose.ui.geometry.Size(step*0.60f,vh))
            }
            fun drawEma(series: List<Double>, color: Color) {
                for (i in 1 until series.size) {
                    val x1=left+step*(i-0.5f); val x2=left+step*(i+0.5f)
                    drawLine(color,Offset(x1,y(series[i-1])),Offset(x2,y(series[i])),2f)
                }
            }
            drawEma(ema9, AMBER); drawEma(ema21, Color(0xFF7CB7FF)); drawEma(ema50, Color(0xFFC39BFF))
        }
        Text("VOLUME • bars scaled within selected window", color=MUTED, fontSize=10.sp)
        Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.spacedBy(12.dp)) {
            Text("● EMA 9", color=AMBER, fontSize=10.sp)
            Text("● EMA 21", color=Color(0xFF7CB7FF), fontSize=10.sp)
            Text("● EMA 50", color=Color(0xFFC39BFF), fontSize=10.sp)
        }
        Divider(color=MUTED.copy(alpha=0.25f))
        Text("RSI 14 • ${analysis?.optString("rsi_14","—") ?: "—"}", fontWeight=FontWeight.SemiBold)
        val rsi = analysis?.optDouble("rsi_14", Double.NaN) ?: Double.NaN
        if (rsi.isFinite()) {
            Box(Modifier.fillMaxWidth().height(10.dp).clip(RoundedCornerShape(8.dp)).background(MUTED.copy(alpha=0.2f))) {
                Box(Modifier.fillMaxWidth((rsi.coerceIn(0.0,100.0)/100.0).toFloat()).fillMaxHeight().background(GREEN))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween) {
                Text("0", color=MUTED, fontSize=10.sp); Text("50", color=MUTED, fontSize=10.sp); Text("100", color=MUTED, fontSize=10.sp)
            }
        }
        Text("MACD ${analysis?.optString("macd","—") ?: "—"}  •  Signal ${analysis?.optString("macd_signal_9","—") ?: "—"}  •  Histogram ${analysis?.optString("macd_histogram","—") ?: "—"}", color=MUTED, fontSize=11.sp)
        Text("These plots use the generated synthetic candles only; no forecasts, trade signals, or real-market prices.", color=AMBER, fontSize=11.sp)
    }
}

@Composable private fun HistoricalIndicatorCards(rawJson: String) {
    val parsed = remember(rawJson) { runCatching { JSONObject(rawJson) }.getOrNull() }
    if (parsed == null) {
        Text("Indicator response could not be parsed.", color=AMBER, fontSize=12.sp)
        return
    }
    val trend = parsed.optString("trend_context", "NOT PROVIDED")
    val rows = listOf(
        "Observations" to parsed.optString("observations", "—"),
        "EMA 9" to parsed.optString("ema_9", "—"),
        "EMA 21" to parsed.optString("ema_21", "—"),
        "EMA 50" to parsed.optString("ema_50", "—"),
        "RSI 14" to parsed.optString("rsi_14", "—"),
        "MACD" to parsed.optString("macd", "—"),
        "MACD signal" to parsed.optString("macd_signal_9", "—"),
        "MACD histogram" to parsed.optString("macd_histogram", "—"),
        "VWAP" to parsed.optString("vwap", "—"),
        "ATR 14" to parsed.optString("atr_14", "—")
    )
    PanelCard {
        Text("HISTORICAL INDICATOR SUMMARY", fontWeight=FontWeight.Bold)
        Text("Trend context: $trend", color=AMBER, fontSize=13.sp, fontWeight=FontWeight.SemiBold)
        rows.chunked(2).forEach { pair ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                pair.forEach { (label, value) ->
                    Column(Modifier.weight(1f).padding(vertical=5.dp)) {
                        Text(label, color=MUTED, fontSize=11.sp)
                        Text(value, color=GREEN, fontSize=14.sp, fontWeight=FontWeight.SemiBold)
                    }
                }
                if (pair.size == 1) Spacer(Modifier.weight(1f))
            }
        }
        val range = parsed.optJSONObject("recent_range_reference")
        if (range != null) {
            Divider(color=MUTED.copy(alpha=0.25f))
            Text("RECENT-RANGE REFERENCES", fontWeight=FontWeight.Bold, fontSize=12.sp)
            StatusRow("Support reference", range.optString("support_zone_reference", "—"))
            StatusRow("Resistance reference", range.optString("resistance_zone_reference", "—"))
        }
        Text("Descriptive calculations on synthetic sample candles only. These are not forecasts or trade signals.", color=AMBER, fontSize=11.sp)
    }
}

@Composable private fun StatusRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth().padding(vertical=6.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
        Text(label,color=MUTED,fontSize=12.sp,modifier=Modifier.weight(1f))
        Text(value,color=if(value in listOf("PRESENT","BACKEND FOUNDATION","AVAILABLE IN BACKEND","CONTRACT READY","PAPER / EDUCATIONAL")) GREEN else AMBER,fontSize=11.sp,fontWeight=FontWeight.SemiBold)
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
private data class CsvMarketData(
    val closes: List<Double> = emptyList(),
    val highs: List<Double> = emptyList(),
    val lows: List<Double> = emptyList(),
    val volumes: List<Double> = emptyList(),
    val volumeAvailable: Boolean = false,
    val error: String? = null
)

private fun splitCsvRow(line: String): List<String> {
    val out = mutableListOf<String>()
    val cell = StringBuilder()
    var quoted = false
    var i = 0
    while (i < line.length) {
        val c = line[i]
        if (c == '"') {
            if (quoted && i + 1 < line.length && line[i + 1] == '"') { cell.append('"'); i++ }
            else quoted = !quoted
        } else if (c == ',' && !quoted) { out.add(cell.toString().trim()); cell.setLength(0) }
        else cell.append(c)
        i++
    }
    out.add(cell.toString().trim())
    return out
}

private fun parseMarketCsv(raw: String): CsvMarketData {
    val lines = raw.lineSequence().map { it.trim().removePrefix("\uFEFF") }.filter { it.isNotBlank() }.toList()
    if (lines.size < 2) return CsvMarketData(error = "CSV needs a header and at least 50 data rows.")
    fun normalize(value: String) = value.trim().trim('"').lowercase()
        .replace("\uFEFF", "").replace(Regex("[^a-z0-9]"), "")
    val headerIndex = lines.indexOfFirst { line ->
        val h = splitCsvRow(line).map(::normalize)
        h.any { it in setOf("date", "indexdate", "tradedate") } &&
            h.any { it in setOf("open", "openindexvalue", "openprice") } &&
            h.any { it in setOf("high", "highindexvalue", "highprice") } &&
            h.any { it in setOf("low", "lowindexvalue", "lowprice") } &&
            h.any { it in setOf("close", "closingindexvalue", "closeindexvalue", "closingprice") }
    }
    if (headerIndex < 0) return CsvMarketData(error = "NSE CSV header not recognised. Expected Date/Open/High/Low/Close or Open/High/Low/Closing Index Value headings.")
    val header = splitCsvRow(lines[headerIndex]).map(::normalize)
    fun col(vararg names: String) = header.indexOfFirst { it in names }
    val dateIdx = col("date", "indexdate", "tradedate")
    val openIdx = col("open", "openindexvalue", "openprice")
    val highIdx = col("high", "highindexvalue", "highprice")
    val lowIdx = col("low", "lowindexvalue", "lowprice")
    val closeIdx = col("close", "closingindexvalue", "closeindexvalue", "closingprice")
    val volumeIdx = col("volume", "tradedquantity", "totaltradedquantity", "totalvolume")
    val dateFormats = listOf("yyyy-MM-dd", "dd MMM yyyy", "dd-MMM-yyyy", "dd-MM-yyyy", "dd/MM/yyyy", "MM/dd/yyyy")
    fun dateKey(value: String): Long? {
        for (pattern in dateFormats) {
            try {
                val fmt = java.text.SimpleDateFormat(pattern, java.util.Locale.ENGLISH).apply { isLenient = false }
                return fmt.parse(value.trim())?.time
            } catch (_: Exception) { }
        }
        return null
    }
    data class Candle(val date: Long, val open: Double, val high: Double, val low: Double, val close: Double, val volume: Double?)
    val candles = mutableListOf<Candle>()
    for ((rowIndex, line) in lines.drop(headerIndex + 1).withIndex()) {
        val cells = splitCsvRow(line)
        if (cells.all { it.isBlank() }) continue
        val dateText = cells.getOrNull(dateIdx)?.trim().orEmpty()
        val date = dateKey(dateText) ?: return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: unsupported or invalid date '$dateText'.")
        fun number(index: Int): Double? = cells.getOrNull(index)?.replace(",", "")?.trim()?.toDoubleOrNull()?.takeIf { it.isFinite() }
        val open = number(openIdx) ?: return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid Open value.")
        val high = number(highIdx) ?: return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid High value.")
        val low = number(lowIdx) ?: return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid Low value.")
        val close = number(closeIdx) ?: return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid Close value.")
        val volume = if (volumeIdx >= 0) number(volumeIdx) else null
        if (volumeIdx >= 0 && (volume == null || volume < 0)) return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid Volume value.")
        if (listOf(open, high, low, close).any { it <= 0 }) return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: OHLC prices must be positive.")
        if (low > minOf(open, close) || high < maxOf(open, close) || low > high) return CsvMarketData(error = "Row ${headerIndex + rowIndex + 2}: invalid OHLC candle geometry.")
        candles.add(Candle(date, open, high, low, close, volume))
    }
    if (candles.size < 50) return CsvMarketData(error = "At least 50 valid OHLC rows are required; found ${candles.size}.")
    val sorted = candles.sortedBy { it.date }
    if (sorted.map { it.date }.distinct().size != sorted.size) return CsvMarketData(error = "CSV contains duplicate dates. Please use one row per trading date.")
    val volumesPresent = sorted.all { it.volume != null }
    return CsvMarketData(
        closes = sorted.map { it.close },
        highs = sorted.map { it.high },
        lows = sorted.map { it.low },
        volumes = if (volumesPresent) sorted.map { it.volume!! } else emptyList(),
        volumeAvailable = volumesPresent
    )
}

@Composable private fun Signals(
    closesText: String,
    onCloses: (String) -> Unit,
    csvRaw: String,
    csvFileName: String,
    onImportCsv: () -> Unit,
    onClear: () -> Unit
) {
    val tokens = closesText.split(Regex("[,\\s]+" )).filter { it.isNotBlank() }
    val parsed = tokens.map { it.trim().toDoubleOrNull() }
    val closes = parsed.filterNotNull().filter { it.isFinite() && it > 0 }
    val invalidCount = parsed.count { it == null || !it.isFinite() || it <= 0 }
    val csv = remember(csvRaw) { if (csvRaw.isBlank()) CsvMarketData() else parseMarketCsv(csvRaw) }
    val e9 = calcEma(closes,9)
    val e21 = calcEma(closes,21)
    val rsiValue = calcRsi(closes,14)
    val recent = closes.takeLast(20)
    val rangeLow = if (recent.size >= 20) recent.minOrNull() else null
    val rangeHigh = if (recent.size >= 20) recent.maxOrNull() else null
    val mid = if (recent.size >= 20) recent.average() else null
    val deviation = if (mid != null) kotlin.math.sqrt(recent.sumOf { (it-mid)*(it-mid) } / recent.size) else null
    val macd = calcEma(closes,12)?.let { fast -> calcEma(closes,26)?.let { slow -> fast-slow } }
    val vwap = if (csv.highs.size == csv.closes.size && csv.lows.size == csv.closes.size && csv.volumes.size == csv.closes.size && csv.volumes.sum() > 0) {
        csv.closes.indices.sumOf { ((csv.highs[it] + csv.lows[it] + csv.closes[it]) / 3.0) * csv.volumes[it] } / csv.volumes.sum()
    } else null
    val trend = if (e9 == null || e21 == null) "Need at least 21 valid closing prices" else if (e9 > e21) "EMA 9 above EMA 21" else if (e9 < e21) "EMA 9 below EMA 21" else "EMAs equal"
    val momentum = when { rsiValue == null -> "Need at least 15 valid closing prices"; rsiValue >= 70 -> "Higher momentum zone (RSI ≥ 70)"; rsiValue <= 30 -> "Lower momentum zone (RSI ≤ 30)"; else -> "Middle RSI zone" }
    LazyColumn(contentPadding=PaddingValues(16.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
        item { PanelCard {
            Text("MARKET ANALYSIS LAB",fontSize=18.sp,fontWeight=FontWeight.Bold)
            Pill("EDUCATIONAL • NOT A TRADE SIGNAL",AMBER)
            Text("Import authorized historical NIFTY OHLC or OHLCV CSV. V6.2 supports index OHLC files without inventing volume; it is not live market data.",color=MUTED,fontSize=13.sp)
            Button(onClick=onImportCsv,modifier=Modifier.fillMaxWidth()) { Text("IMPORT HISTORICAL CSV") }
            if (csvFileName.isNotBlank()) Text("Imported: $csvFileName",color=GREEN,fontSize=12.sp)
            Text("NSE Index CSV supported: Index Name, Date, Open, High, Low, Close (Volume optional) • minimum 50 rows",color=MUTED,fontSize=11.sp)
            OutlinedTextField(value=closesText,onValueChange=onCloses,label={Text("Closing prices (oldest to newest)")},modifier=Modifier.fillMaxWidth(),minLines=3)
            Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically) {
                Text("Valid observations: ${closes.size}",color=MUTED,fontSize=11.sp)
                TextButton(onClick=onClear) { Text("CLEAR INPUT") }
            }
            if (invalidCount > 0) Text("Ignored invalid entries: $invalidCount. Use positive numeric prices only.",color=AMBER,fontSize=11.sp)
            if (csvRaw.isNotBlank() && csv.highs.size != csv.closes.size) Text("CSV imported, but one or more High values are missing or invalid.",color=AMBER,fontSize=11.sp)
            if (closes.size < 50) Text("For EMA 50, enter at least 50 valid observations. Imported/manual data is historical, not live.",color=MUTED,fontSize=11.sp)
        } }
        item { PanelCard {
            Text("INDICATOR SNAPSHOT",fontWeight=FontWeight.Bold)
            Watch("EMA 9",e9?.let { "%.2f".format(it) } ?: "Insufficient data")
            Watch("EMA 21",e21?.let { "%.2f".format(it) } ?: "Insufficient data")
            Watch("RSI 14 (Wilder)",rsiValue?.let { "%.1f".format(it) } ?: "Insufficient data")
            Watch("EMA 50",calcEma(closes,50)?.let { "%.2f".format(it) } ?: "Insufficient data")
            Watch("MACD (12,26)",macd?.let { "%.3f".format(it) } ?: "Insufficient data")
            Watch("Bollinger middle (20)",mid?.let { "%.2f".format(it) } ?: "Insufficient data")
            Watch("Bollinger upper/lower",if(mid!=null && deviation!=null) "%.2f / %.2f".format(mid+2*deviation,mid-2*deviation) else "Insufficient data")
            Watch("20-close range low/high",if(rangeLow!=null && rangeHigh!=null) "%.2f / %.2f".format(rangeLow,rangeHigh) else "Insufficient data")
            Watch("VWAP",vwap?.let { "%.2f".format(it) } ?: "Unavailable: source has no volume")
            Text("Method: SMA-seeded EMA 9/21/50 • Wilder RSI • MACD 12/26 • Bollinger 20 ±2 SD • CSV typical-price VWAP",color=MUTED,fontSize=11.sp)
            Divider(color=Color(0xFF263650))
            Text("Trend context",color=MUTED,fontSize=11.sp);Text(trend,fontWeight=FontWeight.SemiBold)
            Text("Momentum context",color=MUTED,fontSize=11.sp);Text(momentum,fontWeight=FontWeight.SemiBold)
        } }
        item { PanelCard {
            Text("NEWS & SENTIMENT",fontWeight=FontWeight.Bold)
            Pill("NOT CONNECTED",AMBER)
            Text("News impact, market breadth, FII/DII and options sentiment are not connected. They remain unavailable rather than being guessed.",color=MUTED,fontSize=12.sp)
        } }
        item { PanelCard {
            Text("DATA & MODEL LIMITATIONS",fontWeight=FontWeight.Bold)
            Text("This screen analyzes historical closing prices from manual input or an imported CSV. CSV VWAP uses (High+Low+Close)/3 weighted by Volume, when all required fields are valid. It does not produce forecasts or BUY/SELL instructions. Results depend on input quality and do not predict future performance.",color=MUTED,fontSize=12.sp)
        } }
    }
}

private fun calcEma(values:List<Double>,period:Int):Double? {
    if(period < 1 || values.size < period) return null
    val alpha=2.0/(period+1.0)
    var result=values.take(period).average()
    for(v in values.drop(period)) result=alpha*v+(1-alpha)*result
    return result
}
private fun calcRsi(values:List<Double>,period:Int):Double? {
    if(values.size <= period) return null
    val changes=values.zipWithNext { a,b -> b-a }
    var gain=changes.take(period).filter { it>0 }.sum()/period
    var loss=changes.take(period).filter { it<0 }.sum().let { -it/period }
    for(change in changes.drop(period)) {
        gain=((period-1)*gain+maxOf(change,0.0))/period
        loss=((period-1)*loss+maxOf(-change,0.0))/period
    }
    return when { loss==0.0 && gain==0.0 -> 50.0; loss==0.0 -> 100.0; else -> 100.0-(100.0/(1.0+gain/loss)) }
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
