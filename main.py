from datetime import datetime, timezone
from math import isfinite
from typing import Optional
import csv
import io
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from paper import PaperLedger
from analysis import analyze_closes, ema_crossover_backtest
from angel_one import AngelOneMarketDataAdapter

app = FastAPI(
    title="NIFTY AI TRADER PRO — Read-only Educational Market Data",
    version="5.10.0",
)
ledger = PaperLedger(500000)
angel = AngelOneMarketDataAdapter()

INDEX_UNIVERSE = [
    {"symbol": "NIFTY", "name": "NIFTY 50", "segment": "INDEX", "exchange": "NSE"},
    {"symbol": "BANKNIFTY", "name": "NIFTY BANK", "segment": "INDEX", "exchange": "NSE"},
    {"symbol": "FINNIFTY", "name": "NIFTY FINANCIAL SERVICES", "segment": "INDEX", "exchange": "NSE"},
    {"symbol": "MIDCPNIFTY", "name": "NIFTY MIDCAP SELECT", "segment": "INDEX", "exchange": "NSE"},
    {"symbol": "SENSEX", "name": "S&P BSE SENSEX", "segment": "INDEX", "exchange": "BSE"},
    {"symbol": "BANKEX", "name": "BSE BANKEX", "segment": "INDEX", "exchange": "BSE"},
]
DERIVATIVE_COVERAGE = {
    "types": ["FUTURES", "OPTIONS"], "option_sides": ["CE", "PE"],
    "expiry_and_strike_mapping": "REQUIRES_CURRENT_AUTHORIZED_INSTRUMENT_MASTER",
    "exchange_tokens": "NEVER_GUESSED",
}
MAX_REPLAY_ROWS = 5000
MAX_INSTRUMENT_ROWS = 50000
FRESH_SECONDS = 15
DELAYED_SECONDS = 900
clients: set[WebSocket] = set()
latest_event: Optional[dict] = None
instrument_catalogue: list[dict] = []
catalogue_loaded_at: Optional[str] = None
feed_mode = "OFFLINE"
feed_source = "NONE"
feed_note = "No external provider is connected. Historical replay is supported for education only."

class CloseSeries(BaseModel):
    close_prices: list[float] = Field(min_length=1, max_length=10000)

class BacktestRequest(BaseModel):
    close_prices: list[float] = Field(min_length=30, max_length=10000)
    fee_bps: float = Field(default=5.0, ge=0, le=100)

class PaperOrder(BaseModel):
    side: str
    quantity: int = Field(gt=0, le=100000)
    reference_price: float = Field(gt=0)

class MarketEvent(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    last_price: float = Field(gt=0)
    exchange_timestamp: datetime
    delayed: bool = False

def freshness_for(ts: datetime, delayed: bool = False) -> tuple[str, float]:
    if ts.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    age = max(0.0, (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds())
    if delayed:
        return "DELAYED", round(age, 2)
    return ("FRESH" if age <= FRESH_SECONDS else "STALE"), round(age, 2)

async def broadcast(payload: dict):
    stale_clients = []
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale_clients.append(ws)
    for ws in stale_clients:
        clients.discard(ws)

@app.get("/api/health")
async def health():
    return {"status":"ok","service":"nifty-ai-trader-pro-backend","version":"5.10.0",
            "mode":"EDUCATIONAL_PAPER_ONLY","real_orders_enabled":False,"virtual_capital":500000}

@app.get("/api/v5/integration-status")
async def integration_status():
    try:
        angel_status = await angel.status()
    except Exception:
        angel_status = {"provider":"Angel One SmartAPI","connected":False,"configured":False,
                        "mode":"OFFLINE_NOT_CONFIGURED","read_only":True}
    return {
        "app_version":"5.10.0","integration_foundation":"READ_ONLY_EDUCATIONAL_FEED_READY",
        "angel_one":angel_status,
        "authorized_provider":{"connected":False,"mode":"NOT_CONFIGURED",
          "message":"No external authorized provider is connected by this educational build."},
        "stream":{"endpoint":"/ws/market","status":"AVAILABLE_FOR_HISTORICAL_REPLAY",
                  "connected_clients":len(clients)},
        "supported_indices":[x["symbol"] for x in INDEX_UNIVERSE],
        "derivatives":DERIVATIVE_COVERAGE,"live_data_verified":False,
        "real_orders_enabled":False,"mode":"EDUCATIONAL_PAPER_ONLY"
    }

@app.get("/api/providers/angel-one")
async def provider_status():
    try:
        return await angel.status()
    except Exception:
        return {"provider":"Angel One SmartAPI","connected":False,"configured":False,
                "mode":"OFFLINE_NOT_CONFIGURED","read_only":True,"real_orders_enabled":False}

@app.get("/api/market/universe")
async def market_universe():
    return {"status":"COVERAGE_TARGETS_ONLY","live_data":False,"indices":INDEX_UNIVERSE,
            "derivatives":DERIVATIVE_COVERAGE,
            "instrument_master":{"loaded":bool(instrument_catalogue),"count":len(instrument_catalogue),
                                 "loaded_at":catalogue_loaded_at},
            "note":"Index names are coverage targets, not exchange tokens. Derivative contracts require a current authorized instrument-master CSV."}

@app.post("/api/market/instrument-master")
async def load_instrument_master(csv_text: str = Body(..., media_type="text/plain")):
    """Load a user-supplied authorized instrument-master CSV. No tokens or contracts are invented."""
    global instrument_catalogue, catalogue_loaded_at
    if len(csv_text) > 20_000_000:
        raise HTTPException(413, "CSV exceeds 20 MB limit")
    reader = csv.DictReader(io.StringIO(csv_text))
    required = {"symbol","exchange","segment","instrument_token","expiry","strike","option_type"}
    headers = set(reader.fieldnames or [])
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(400, {"error":"missing_required_columns","missing":missing})
    rows=[]
    for line_no, row in enumerate(reader, start=2):
        if len(rows) >= MAX_INSTRUMENT_ROWS:
            raise HTTPException(413, "Too many instrument rows")
        symbol=(row.get("symbol") or "").strip().upper()
        token=(row.get("instrument_token") or "").strip()
        exchange=(row.get("exchange") or "").strip().upper()
        segment=(row.get("segment") or "").strip().upper()
        opt=(row.get("option_type") or "").strip().upper()
        if not symbol or not token or exchange not in {"NSE","BSE"}:
            raise HTTPException(400, f"Invalid symbol/token/exchange at CSV line {line_no}")
        if opt and opt not in {"CE","PE"}:
            raise HTTPException(400, f"Invalid option_type at CSV line {line_no}")
        rows.append({k:(v or "").strip() for k,v in row.items() if k in required})
    if not rows:
        raise HTTPException(400, "Instrument master contains no rows")
    instrument_catalogue=rows
    catalogue_loaded_at=datetime.now(timezone.utc).isoformat()
    return {"status":"LOADED","count":len(rows),"loaded_at":catalogue_loaded_at,
            "source":"USER_SUPPLIED_AUTHORIZED_CSV","live_data":False,
            "note":"Catalogue metadata only; this does not connect a market feed."}

@app.get("/api/market/instruments")
async def list_instruments(symbol: Optional[str]=None, segment: Optional[str]=None):
    rows=instrument_catalogue
    if symbol: rows=[r for r in rows if r["symbol"].upper()==symbol.upper()]
    if segment: rows=[r for r in rows if r["segment"].upper()==segment.upper()]
    return {"count":len(rows),"source":"USER_SUPPLIED_AUTHORIZED_CSV" if instrument_catalogue else "NONE",
            "live_data":False,"instruments":rows[:2000]}

@app.get("/api/market/feed-status")
async def market_feed_status():
    global latest_event
    if latest_event:
        ts=datetime.fromisoformat(latest_event["exchange_timestamp"])
        fresh, age=freshness_for(ts, latest_event.get("delayed",False))
        return {"status":"HISTORICAL_REPLAY","source":"USER_SUPPLIED_CSV_REPLAY",
                "connected":False,"last_event_at":latest_event["exchange_timestamp"],
                "freshness":fresh,"age_seconds":age,"read_only":True,"live_data_verified":False,
                "websocket_clients":len(clients),
                "message":"Educational historical replay only; not a live market feed."}
    return {"status":"OFFLINE","source":"NONE","connected":False,"last_event_at":None,
            "freshness":"NO_DATA","read_only":True,"live_data_verified":False,
            "websocket_clients":len(clients),
            "message":"No live provider connected. Upload historical CSV replay to test the Android stream."}

@app.get("/api/market")
async def market():
    if latest_event:
        return {**latest_event,"status":"HISTORICAL_REPLAY","read_only":True,
                "live_data_verified":False,"note":"Historical replay, not live market data."}
    return {"symbol":"NIFTY","value":None,"source":"NO_LIVE_FEED","status":"OFFLINE",
            "read_only":True,"timestamp":None,"note":"No live feed is configured."}

@app.post("/api/market/validate-event")
async def validate_market_event(event: MarketEvent):
    try: fresh, age=freshness_for(event.exchange_timestamp,event.delayed)
    except ValueError as exc: raise HTTPException(400,str(exc))
    return {"valid":True,"symbol":event.symbol.strip().upper(),"last_price":event.last_price,
            "exchange_timestamp":event.exchange_timestamp.isoformat(),"age_seconds":age,
            "freshness":fresh,"source":"VALIDATION_ONLY","read_only":True,
            "note":"Validation only; not stored as a live quote."}

@app.post("/api/market/replay-csv")
async def replay_csv(csv_text: str = Body(..., media_type="text/plain")):
    """Replay user-supplied historical CSV rows over the WebSocket, explicitly labelled historical."""
    global latest_event
    if len(csv_text)>5_000_000: raise HTTPException(413,"CSV exceeds 5 MB limit")
    reader=csv.DictReader(io.StringIO(csv_text))
    required={"symbol","timestamp","last_price"}
    missing=sorted(required-set(reader.fieldnames or []))
    if missing: raise HTTPException(400,{"error":"missing_required_columns","missing":missing})
    parsed=[]
    for line_no,row in enumerate(reader,start=2):
        if len(parsed)>=MAX_REPLAY_ROWS: raise HTTPException(413,"Maximum 5000 replay rows")
        try:
            ts=datetime.fromisoformat((row.get("timestamp") or "").strip().replace("Z","+00:00"))
            if ts.tzinfo is None: raise ValueError("timestamp timezone missing")
            price=float(row.get("last_price",""))
            symbol=(row.get("symbol") or "").strip().upper()
            if not symbol or not isfinite(price) or price<=0: raise ValueError("invalid symbol or price")
        except Exception as exc:
            raise HTTPException(400,f"Invalid CSV row {line_no}: {exc}")
        parsed.append({"type":"market_event","symbol":symbol,"last_price":price,
                       "exchange_timestamp":ts.isoformat(),"delayed":True,
                       "source":"USER_SUPPLIED_CSV_REPLAY","mode":"HISTORICAL_REPLAY",
                       "read_only":True,"live_data_verified":False})
    if not parsed: raise HTTPException(400,"CSV contains no data rows")
    for event in parsed:
        latest_event=event
        await broadcast(event)
        await asyncio.sleep(0)
    return {"status":"REPLAY_COMPLETE","rows_replayed":len(parsed),
            "source":"USER_SUPPLIED_CSV_REPLAY","live_data_verified":False,
            "websocket_clients":len(clients),
            "note":"Historical rows were replayed to connected WebSocket clients. This is not live data."}

@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        await websocket.send_json({"type":"status","status":"CONNECTED",
            "mode":"HISTORICAL_REPLAY_ONLY","read_only":True,"live_data_verified":False,
            "message":"Socket connected. It receives only explicitly labelled CSV replay events."})
        if latest_event:
            await websocket.send_json(latest_event)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)

@app.post("/api/analysis/indicators")
async def indicators(data: CloseSeries):
    try: return analyze_closes(data.close_prices)
    except ValueError as exc: raise HTTPException(400,str(exc))

@app.post("/api/backtest/ema-crossover")
async def backtest(data: BacktestRequest):
    try: return ema_crossover_backtest(data.close_prices,data.fee_bps)
    except ValueError as exc: raise HTTPException(400,str(exc))

@app.get("/api/paper/ledger")
async def get_ledger(): return ledger.snapshot()

@app.post("/api/paper/order")
async def paper_order(order: PaperOrder):
    try: return ledger.record(order.side,order.quantity,order.reference_price)
    except ValueError as exc: raise HTTPException(400,str(exc))

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>NIFTY AI TRADER PRO</title><style>body{background:#080d18;color:#e8eefc;font:16px Arial;padding:22px}
    .card{background:#121c2e;border:1px solid #263650;border-radius:14px;padding:16px;margin:12px 0}
    .muted{color:#9aabc7}.warn{color:#f5c76b}</style></head><body><h1>NIFTY AI TRADER PRO</h1>
    <p class='warn'>EDUCATIONAL • PAPER MODE ONLY • NO LIVE FEED</p>
    <div class='card'><h3>Feed status</h3><p id='feed' class='muted'>Checking…</p></div>
    <div class='card'><h3>Coverage targets</h3><p id='coverage' class='muted'>Loading…</p></div>
    <script>async function load(){let f=await(await fetch('/api/market/feed-status')).json();
    document.getElementById('feed').textContent=f.status+' — '+f.message;
    let c=await(await fetch('/api/market/universe')).json();
    document.getElementById('coverage').textContent=c.indices.map(x=>x.name).join(', ');}load();</script></body></html>"""
