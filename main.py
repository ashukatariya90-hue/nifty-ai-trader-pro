from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from paper import PaperLedger
from analysis import analyze_closes, ema_crossover_backtest
from angel_one import AngelOneMarketDataAdapter
app = FastAPI(title="NIFTY AI TRADER PRO — Paper Trading", version="3.0.0")
ledger = PaperLedger(500000)
angel = AngelOneMarketDataAdapter()

class CloseSeries(BaseModel):
    close_prices: list[float] = Field(min_length=1, max_length=10000)

class BacktestRequest(BaseModel):
    close_prices: list[float] = Field(min_length=30, max_length=10000)
    fee_bps: float = Field(default=5.0, ge=0, le=100)

class PaperOrder(BaseModel):
    side: str
    quantity: int = Field(gt=0, le=100000)
    reference_price: float = Field(gt=0)

@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "LIVE_DATA_ARCHITECTURE_PAPER_ONLY",
            "real_orders_enabled": False, "virtual_capital": 500000}

@app.get("/api/providers/angel-one")
async def provider_status():
    return await angel.status()

@app.get("/api/market")
async def market():
    return {"symbol": "NIFTY", "value": None, "source": "NO_LIVE_FEED",
            "note": "Live feed is not configured; no synthetic value is labelled as live."}


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
    <div class='card'><h3>Angel One Provider</h3><p id='provider' class='muted'>Loading…</p></div>
    <div class='card'><h3>Market feed</h3><p id='market' class='muted'>Loading…</p></div>
    <div class='card'><h3>Virtual portfolio</h3><p id='ledger' class='muted'>Loading…</p></div>
    <script>async function load(){let p=await(await fetch('/api/providers/angel-one')).json();
    document.getElementById('provider').textContent=p.message;
    let m=await(await fetch('/api/market')).json();document.getElementById('market').textContent=m.note;
    let l=await(await fetch('/api/paper/ledger')).json();document.getElementById('ledger').textContent='Virtual balance ₹'+l.virtual_balance+' | Records '+l.orders.length;}
    load();</script></body></html>"""
