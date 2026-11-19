from datetime import datetime, timezone
from math import isfinite

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from paper import PaperLedger
from analysis import analyze_closes, ema_crossover_backtest
from angel_one import AngelOneMarketDataAdapter

app = FastAPI(
    title="NIFTY AI TRADER PRO — Market Data Foundation",
    version="5.9.0",
)
ledger = PaperLedger(500000)
angel = AngelOneMarketDataAdapter()

# Coverage targets only. These are NOT exchange instrument tokens or live contracts.
INDEX_UNIVERSE = [
    {"symbol": "NIFTY", "name": "NIFTY 50", "segment": "INDEX"},
    {"symbol": "BANKNIFTY", "name": "NIFTY BANK", "segment": "INDEX"},
    {"symbol": "FINNIFTY", "name": "NIFTY FINANCIAL SERVICES", "segment": "INDEX"},
    {"symbol": "MIDCPNIFTY", "name": "NIFTY MIDCAP SELECT", "segment": "INDEX"},
    {"symbol": "SENSEX", "name": "S&P BSE SENSEX", "segment": "INDEX"},
    {"symbol": "BANKEX", "name": "BSE BANKEX", "segment": "INDEX"},
]

DERIVATIVE_COVERAGE = {
    "types": ["FUTURES", "OPTIONS"],
    "option_sides": ["CE", "PE"],
    "expiry_and_strike_mapping": "PENDING_AUTHORIZED_INSTRUMENT_MASTER",
    "exchange_tokens": "NOT_INCLUDED_OR_GUESSED",
}

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

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "service": "nifty-ai-trader-pro-backend",
        "version": "5.9.0",
        "mode": "EDUCATIONAL_PAPER_ONLY",
        "real_orders_enabled": False,
        "virtual_capital": 500000,
    }

@app.get("/api/v5/integration-status")
async def integration_status():
    try:
        angel_status = await angel.status()
    except Exception:
        angel_status = {
            "provider": "Angel One SmartAPI",
            "connected": False,
            "configured": False,
            "mode": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "message": "Provider adapter status unavailable; no live feed is connected.",
        }
    return {
        "app_version": "5.9.0",
        "integration_foundation": "MARKET_DATA_FOUNDATION_READY",
        "angel_one": angel_status,
        "authorized_provider": {
            "connected": False,
            "mode": "NOT_CONFIGURED",
            "message": "No authorized market-data feed is connected.",
        },
        "stream": {
            "endpoint": "/ws/market",
            "status": "OFFLINE_NOT_CONFIGURED",
            "connected_clients": 0,
        },
        "supported_indices": [item["symbol"] for item in INDEX_UNIVERSE],
        "derivatives": DERIVATIVE_COVERAGE,
        "live_data_verified": False,
        "real_orders_enabled": False,
        "mode": "EDUCATIONAL_PAPER_ONLY",
    }

@app.get("/api/providers/angel-one")
async def provider_status():
    try:
        return await angel.status()
    except Exception:
        return {
            "provider": "Angel One SmartAPI",
            "connected": False,
            "configured": False,
            "mode": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "real_orders_enabled": False,
            "message": "No authenticated or authorized market-data feed is connected.",
        }

@app.get("/api/market/universe")
async def market_universe():
    return {
        "status": "CATALOG_TARGETS_ONLY",
        "live_data": False,
        "indices": INDEX_UNIVERSE,
        "derivatives": DERIVATIVE_COVERAGE,
        "note": "This is a coverage list, not a live quote list. Contract tokens, strikes and expiries must come from a current authorized instrument master.",
    }

@app.get("/api/market/feed-status")
async def market_feed_status():
    return {
        "status": "OFFLINE",
        "source": "NONE",
        "connected": False,
        "last_event_at": None,
        "freshness": "NO_DATA",
        "read_only": True,
        "live_data_verified": False,
        "message": "No live market-data provider is connected.",
    }

@app.get("/api/market")
async def market():
    return {
        "symbol": "NIFTY",
        "value": None,
        "source": "NO_LIVE_FEED",
        "status": "OFFLINE",
        "read_only": True,
        "timestamp": None,
        "note": "Live feed is not configured; no synthetic value is labelled as live.",
    }

@app.post("/api/market/validate-event")
async def validate_market_event(event: MarketEvent):
    now = datetime.now(timezone.utc)
    ts = event.exchange_timestamp
    if ts.tzinfo is None:
        raise HTTPException(status_code=400, detail="exchange_timestamp must include timezone")
    age = max(0.0, (now - ts.astimezone(timezone.utc)).total_seconds())
    return {
        "valid": True,
        "symbol": event.symbol.strip().upper(),
        "last_price": event.last_price,
        "exchange_timestamp": ts.isoformat(),
        "age_seconds": round(age, 2),
        "freshness": "FRESH" if age <= 15 and not event.delayed else ("DELAYED" if event.delayed else "STALE"),
        "source": "VALIDATION_ONLY",
        "read_only": True,
        "note": "Validation test only. This event is not stored or represented as a connected live feed.",
    }

@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        await websocket.send_json({
            "type": "status",
            "status": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "message": "WebSocket endpoint is reachable, but no provider is connected.",
        })
        while True:
            # Client pings keep the test socket open. No market ticks are fabricated.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass

@app.post("/api/analysis/indicators")
async def indicators(data: CloseSeries):
    try:
        return analyze_closes(data.close_prices)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/backtest/ema-crossover")
async def backtest(data: BacktestRequest):
    try:
        return ema_crossover_backtest(data.close_prices, data.fee_bps)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/api/paper/ledger")
async def get_ledger():
    return ledger.snapshot()

@app.post("/api/paper/order")
async def paper_order(order: PaperOrder):
    try:
        return ledger.record(order.side, order.quantity, order.reference_price)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>NIFTY AI TRADER PRO</title><style>
    body{background:#080d18;color:#e8eefc;font:16px Arial;padding:22px}
    .card{background:#121c2e;border:1px solid #263650;border-radius:14px;padding:16px;margin:12px 0}
    .muted{color:#9aabc7}.warn{color:#f5c76b}
    </style></head><body><h1>NIFTY AI TRADER PRO</h1>
    <p class='warn'>₹5,00,000 VIRTUAL CAPITAL • PAPER MODE ONLY</p>
    <div class='card'><h3>Market Feed</h3><p id='feed' class='muted'>Checking…</p></div>
    <div class='card'><h3>Coverage</h3><p id='coverage' class='muted'>Loading…</p></div>
    <script>async function load(){let f=await(await fetch('/api/market/feed-status')).json();
    document.getElementById('feed').textContent=f.status+' — '+f.message;
    let c=await(await fetch('/api/market/universe')).json();
    document.getElementById('coverage').textContent=c.indices.map(x=>x.name).join(', ');}
    load();</script></body></html>"""
