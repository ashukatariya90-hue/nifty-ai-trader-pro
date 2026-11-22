from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .paper import PaperLedger
from .analysis import analyze_closes, ema_crossover_backtest
from .advanced_analysis import analyze_market_context
from .multifactor import analyze_factors
from .historical_validation import validate_ohlcv_rows
from .walk_forward import evaluate_walk_forward
from .historical_research import analyze_historical_csv as run_historical_csv_research
import csv
import io
import random
import asyncio
import uuid
from datetime import timedelta, timezone
from datetime import datetime
from .providers.authorized_feed import AuthorizedFeedAdapter
from .providers.angel_one import AngelOneMarketDataAdapter
from .providers.news_sentiment import NewsSentimentProvider
from .providers.stream_manager import MarketStreamManager
from .providers.contracts import parse_tick
from .providers.nse_mcp import discover_tools, call_readonly_tool

app = FastAPI(title="NIFTY AI TRADER PRO — Read-only Market Intelligence", version="6.8.0")
ledger = PaperLedger(500000)
market_provider = AuthorizedFeedAdapter()
angel_one_provider = AngelOneMarketDataAdapter()
news_provider = NewsSentimentProvider()
stream_manager = MarketStreamManager()
historical_replays: dict[str, dict] = {}

class CloseSeries(BaseModel):
    close_prices: list[float] = Field(min_length=1, max_length=10000)

class CandleSeries(BaseModel):
    high: list[float] = Field(min_length=2, max_length=10000)
    low: list[float] = Field(min_length=2, max_length=10000)
    close: list[float] = Field(min_length=2, max_length=10000)
    volume: list[float] | None = Field(default=None, max_length=10000)

class BacktestRequest(BaseModel):
    close_prices: list[float] = Field(min_length=30, max_length=10000)
    fee_bps: float = Field(default=5.0, ge=0, le=100)

class HistoricalDataset(BaseModel):
    rows: list[dict] = Field(min_length=2, max_length=20000)
    interval_seconds: int | None = Field(default=None, gt=0)

class WalkForwardRequest(BaseModel):
    close_prices: list[float] = Field(min_length=31, max_length=20000)
    min_history: int = Field(default=30, ge=22, le=5000)

class PaperOrder(BaseModel):
    side: str
    quantity: int = Field(gt=0, le=100000)
    reference_price: float = Field(gt=0)
    symbol: str = Field(default="NIFTY", min_length=1, max_length=40)
    client_order_id: str | None = Field(default=None, max_length=80)


@app.get("/api/nse/status")
async def nse_public_status():
    """Discover NSE's public read-only educational data tools."""
    return await discover_tools()

@app.post("/api/nse/query")
async def nse_public_query(payload: dict):
    """Call an allowlisted NSE informational tool; never routes orders."""
    server = payload.get("server", "cm_market")
    tool_name = payload.get("tool")
    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=400, detail="arguments must be an object")
    try:
        return await call_readonly_tool(server, tool_name, arguments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"NSE data unavailable: {str(exc)[:200]}")

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "nifty-ai-trader-pro-backend", "version": "6.8.0",
            "mode": "EDUCATIONAL_PAPER_ONLY", "real_orders_enabled": False, "virtual_capital": 500000}

@app.get("/api/providers/status")
async def provider_status():
    return market_provider.status()

@app.get("/api/providers/angel-one")
async def legacy_provider_status():
    return await angel_one_provider.status()



@app.get("/api/simulation/status")
async def simulation_status():
    return {"mode": "SIMULATED_ONLY", "symbol": "NIFTY", "baseline": 25000.0,
            "market_data_is_real": False, "real_orders_enabled": False,
            "message": "Synthetic educational data only; not exchange prices."}

@app.get("/api/simulation/snapshot")
async def simulation_snapshot(seed: int = 20261121):
    """Create a deterministic, explicitly synthetic snapshot for UI and paper testing."""
    rng = random.Random(seed)
    price = round(25000.0 + rng.uniform(-180, 180), 2)
    now = datetime.now(timezone.utc)
    tick = parse_tick({"symbol": "NIFTY", "last_price": price,
                       "exchange_timestamp": now.isoformat()}, source="SIMULATED_RANDOM_WALK")
    await stream_manager.publish(tick)
    return {"symbol": "NIFTY", "last_price": price, "source": "SIMULATED_RANDOM_WALK",
            "exchange_timestamp": now.isoformat(), "data_type": "SYNTHETIC_NOT_MARKET_DATA",
            "read_only": True, "real_orders_enabled": False,
            "note": "Generated test value. It is not a live or historical NIFTY quote."}

@app.get("/api/simulation/historical-sample")
async def simulation_historical_sample(seed: int = 20261121, count: int = 80):
    """Return deterministic synthetic OHLCV candles for historical-analysis UI testing."""
    if count < 30 or count > 500:
        raise HTTPException(status_code=400, detail="count must be between 30 and 500")
    rng = random.Random(seed)
    price = 25000.0
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    for i in range(count):
        change = rng.uniform(-24, 24)
        open_price = price
        close_price = max(100.0, open_price + change)
        high = max(open_price, close_price) + rng.uniform(1, 12)
        low = min(open_price, close_price) - rng.uniform(1, 12)
        candles.append({"date": (start + timedelta(minutes=5*i)).isoformat(),
                        "open": round(open_price, 2), "high": round(high, 2),
                        "low": round(low, 2), "close": round(close_price, 2),
                        "volume": rng.randint(1000, 50000)})
        price = close_price
    return {"symbol": "NIFTY", "source": "SYNTHETIC_HISTORICAL_SAMPLE",
            "data_type": "SYNTHETIC_NOT_HISTORICAL_MARKET_DATA", "candles": candles,
            "analysis_endpoint": "/api/analysis/market-context",
            "read_only": True, "real_orders_enabled": False,
            "note": "Synthetic candles for software testing only; not NSE historical data."}

@app.get("/api/market")
async def market():
    latest = stream_manager.latest_snapshot("NIFTY")
    event = latest["events"].get("NIFTY")
    if event:
        return {"symbol": "NIFTY", "value": event["last_price"],
                "source": event["source"], "status": event["freshness"],
                "exchange_timestamp": event["exchange_timestamp"],
                "read_only": True, "real_orders_enabled": False,
                "note": "Latest validated provider event. Verify freshness before interpreting."}
    return {
        "symbol": "NIFTY", "value": None, "source": "NO_LIVE_FEED",
        "status": "OFFLINE", "read_only": True, "real_orders_enabled": False,
        "note": "No validated provider event is cached. No synthetic value is labelled as live."
    }

@app.get("/api/market/latest")
async def latest_market_events(symbol: str | None = None):
    """Return cached validated events and their current freshness classification."""
    return stream_manager.latest_snapshot(symbol)

@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await stream_manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "status", "status": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "message": "Stream endpoint is ready for validated provider events; no provider is connected."
        })
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=20)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "server_timestamp": datetime.now(timezone.utc).isoformat(),
                    "read_only": True,
                    "real_orders_enabled": False,
                })
                stream_manager._metrics["heartbeat_messages_sent"] += 1
    except WebSocketDisconnect:
        await stream_manager.disconnect(websocket)
    except Exception:
        await stream_manager.disconnect(websocket)


@app.get("/api/v6/stream-health")
async def v6_stream_health():
    """Read-only stream health summary with explicit freshness and no provider assumptions."""
    status = stream_manager.status()
    snapshot = stream_manager.latest_snapshot()
    event_states = {symbol: event["freshness"] for symbol, event in snapshot["events"].items()}
    return {
        "app_version": "6.8.0",
        "stream_status": snapshot["status"],
        "connected_clients": status["connected_clients"],
        "symbols_cached": status["symbols_cached"],
        "event_freshness": event_states,
        "metrics": status["metrics"],
        "heartbeat_interval_seconds": status["heartbeat_interval_seconds"],
        "provider_connected": False,
        "live_data_verified": False,
        "read_only": True,
        "real_orders_enabled": False,
        "note": "Heartbeat confirms WebSocket server responsiveness only; it does not establish a market-data provider connection."
    }


@app.get("/api/v6/diagnostics")
async def v6_diagnostics():
    """Operational diagnostics for the read-only stream; no credentials or orders."""
    return {
        "app_version": "6.8.0",
        "mode": "EDUCATIONAL_PAPER_ONLY",
        "stream": stream_manager.status(),
        "provider_connections": {
            "angel_one": (await angel_one_provider.status()),
            "authorized_provider": market_provider.status(),
            "news_sentiment": await news_provider.status(),
        },
        "live_data_verified": False,
        "real_orders_enabled": False,
    }


@app.get("/api/v5/integration-status")
async def integration_status():
    return {
        "app_version": "6.8.0",
        "integration_foundation": "READY_FOR_PROVIDER_IMPLEMENTATION",
        "angel_one": await angel_one_provider.status(),
        "authorized_provider": market_provider.status(),
        "news_sentiment": await news_provider.status(),
        "stream": stream_manager.status(),
        "diagnostics": stream_manager.status(),
        "real_orders_enabled": False,
        "live_data_verified": False
    }

@app.get("/api/news-sentiment/status")
async def news_sentiment_status():
    return await news_provider.status()

@app.post("/api/market/validate-event")
async def validate_market_event(payload: dict = Body(...)):
    try:
        tick = parse_tick(payload, source="VALIDATION_ONLY")
        return {
            "valid": True, "symbol": tick.symbol, "last_price": tick.last_price,
            "exchange_timestamp": tick.exchange_timestamp.isoformat(),
            "freshness": tick.freshness, "read_only": True,
            "note": "Validation only; this is not a connected live feed."
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/analysis/indicators")
async def indicators(data: CloseSeries):
    try:
        return analyze_closes(data.close_prices)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/analysis/market-context")
async def market_context(data: CandleSeries):
    try:
        return analyze_market_context(data.high, data.low, data.close, data.volume)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/research/historical-csv")
async def historical_csv_research(csv_text: str = Body(..., media_type="text/csv")):
    """Run structural validation, multi-factor context and walk-forward diagnostics on a supplied CSV."""
    try:
        return run_historical_csv_research(csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/replay/historical-csv")
async def start_historical_replay(
    csv_text: str = Body(..., media_type="text/csv"),
    interval_ms: int = 250,
):
    """Start a labelled, read-only replay of user-supplied historical NSE OHLC data."""
    if interval_ms < 50 or interval_ms > 5000:
        raise HTTPException(status_code=400, detail="interval_ms must be between 50 and 5000")
    try:
        research = run_historical_csv_research(csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # A replay is a separate session; remove a newer synthetic/test event first.
    for task_id, state in list(historical_replays.items()):
        if state.get("status") == "RUNNING":
            state["status"] = "CANCELLED"
            task = state.get("task")
            if task and not task.done():
                task.cancel()
    await stream_manager.clear("NIFTY")
    replay_id = str(uuid.uuid4())
    candles = research["replay_candles"]
    historical_replays[replay_id] = {
        "status": "RUNNING", "total": len(candles), "published": 0,
        "source": "USER_SUPPLIED_HISTORICAL_CSV", "classification": "HISTORICAL_REPLAY_NOT_LIVE",
        "started_at": datetime.now(timezone.utc).isoformat(), "task": None,
    }

    async def run_replay():
        state = historical_replays[replay_id]
        try:
            for candle in candles:
                tick = parse_tick({
                    "symbol": "NIFTY", "last_price": candle["close"],
                    "exchange_timestamp": candle["timestamp"], "delayed": True,
                }, source="HISTORICAL_CSV_REPLAY")
                accepted = await stream_manager.publish(tick)
                if accepted:
                    state["published"] += 1
                await asyncio.sleep(interval_ms / 1000)
            state["status"] = "COMPLETED"
            state["completed_at"] = datetime.now(timezone.utc).isoformat()
        except asyncio.CancelledError:
            state["status"] = "CANCELLED"
            raise
        except Exception as exc:
            state["status"] = "FAILED"
            state["error"] = str(exc)[:200]

    task = asyncio.create_task(run_replay())
    historical_replays[replay_id]["task"] = task
    return {
        "replay_id": replay_id, "status": "RUNNING", "total": len(candles),
        "published": 0, "source": "USER_SUPPLIED_HISTORICAL_CSV",
        "classification": "HISTORICAL_REPLAY_NOT_LIVE", "interval_ms": interval_ms,
        "real_orders_enabled": False, "paper_only": True,
        "note": "Replay preserves supplied timestamps. All events are labelled historical and delayed.",
    }

@app.get("/api/replay/{replay_id}")
async def historical_replay_status(replay_id: str):
    state = historical_replays.get(replay_id)
    if not state:
        raise HTTPException(status_code=404, detail="Replay session not found")
    return {key: value for key, value in state.items() if key != "task"} | {
        "real_orders_enabled": False, "paper_only": True,
    }

@app.post("/api/replay/{replay_id}/stop")
async def stop_historical_replay(replay_id: str):
    state = historical_replays.get(replay_id)
    if not state:
        raise HTTPException(status_code=404, detail="Replay session not found")
    task = state.get("task")
    if task and not task.done():
        task.cancel()
    state["status"] = "CANCELLED"
    return {"replay_id": replay_id, "status": "CANCELLED", "real_orders_enabled": False}

@app.post("/api/analysis/validate-dataset")
async def validate_historical_dataset(payload: HistoricalDataset):
    """Check OHLCV structure, timestamps and optional interval gaps; does not authenticate data."""
    try:
        return validate_ohlcv_rows(payload.rows, payload.interval_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/research/walk-forward")
async def walk_forward_research(payload: WalkForwardRequest):
    """Chronological next-bar classification diagnostics; no orders or trading advice."""
    try:
        return evaluate_walk_forward(payload.close_prices, payload.min_history)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/analysis/multi-factor")
async def multi_factor_analysis(payload: CandleSeries):
    """Return transparent descriptive factor agreement; never a trading signal."""
    try:
        return analyze_factors(payload.high, payload.low, payload.close, payload.volume)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/analysis/csv")
async def analyze_historical_csv(csv_text: str = Body(..., media_type="text/csv")):
    """Validate an authorized historical OHLCV CSV and return descriptive metrics only."""
    if len(csv_text.encode("utf-8")) > 2_000_000:
        raise HTTPException(status_code=413, detail="CSV exceeds 2 MB limit")
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        required = ["date", "open", "high", "low", "close", "volume"]
        if not reader.fieldnames:
            raise ValueError("CSV header is missing")
        normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
        missing = [name for name in required if name not in normalized]
        if missing:
            raise ValueError("missing required columns: " + ", ".join(missing))
        rows = []
        for line_no, row in enumerate(reader, start=2):
            try:
                date_text = (row[normalized["date"]] or "").strip()
                # Accept ISO dates and ISO timestamps, but reject unparseable dates.
                datetime.fromisoformat(date_text.replace("Z", "+00:00"))
                candle = {key: float(row[normalized[key]]) for key in required[1:]}
            except Exception as exc:
                raise ValueError(f"invalid row {line_no}: {exc}")
            if any(not __import__("math").isfinite(v) for v in candle.values()):
                raise ValueError(f"row {line_no} contains non-finite values")
            if candle["open"] <= 0 or candle["high"] <= 0 or candle["low"] <= 0 or candle["close"] <= 0 or candle["volume"] < 0:
                raise ValueError(f"row {line_no} contains out-of-range values")
            if candle["low"] > candle["high"] or not candle["low"] <= candle["open"] <= candle["high"] or not candle["low"] <= candle["close"] <= candle["high"]:
                raise ValueError(f"row {line_no} violates OHLC bounds")
            rows.append((date_text, candle))
        if len(rows) < 2:
            raise ValueError("at least two valid OHLCV rows are required")
        dates = [datetime.fromisoformat(item[0].replace("Z", "+00:00")) for item in rows]
        if any(dates[i] <= dates[i-1] for i in range(1, len(dates))):
            raise ValueError("dates must be strictly increasing with no duplicates")
        values = {key: [item[1][key] for item in rows] for key in required[1:]}
        result = analyze_market_context(values["high"], values["low"], values["close"], values["volume"])
        result["data_quality"] = {
            "status": "VALIDATED_HISTORICAL_CSV",
            "rows": len(rows),
            "first_date": rows[0][0],
            "last_date": rows[-1][0],
            "strictly_increasing_dates": True,
            "ohlc_bounds_valid": True,
            "volume_column_present": True,
        }
        result["data_basis"] = "USER_SUPPLIED_HISTORICAL_CSV"
        result["is_trade_signal"] = False
        return result
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

@app.post("/api/paper/orders")
async def submit_paper_order(order: PaperOrder):
    """Create a pending paper order; this endpoint never contacts a broker."""
    try:
        return ledger.submit(order.side, order.quantity, order.reference_price,
                             order.symbol, order.client_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/paper/orders/{order_id}/fill")
async def fill_paper_order(order_id: str, payload: dict = Body(default={})):
    try:
        return ledger.fill(order_id, payload.get("fill_price"))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/api/paper/orders/{order_id}/cancel")
async def cancel_paper_order(order_id: str):
    try:
        return ledger.cancel(order_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

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
    <script>async function load(){let p=await(await fetch('/api/providers/status')).json();
    document.getElementById('provider').textContent=p.message;
    let m=await(await fetch('/api/market')).json();document.getElementById('market').textContent=m.note;
    let l=await(await fetch('/api/paper/ledger')).json();document.getElementById('ledger').textContent='Virtual balance ₹'+l.virtual_balance+' | Records '+l.orders.length;}
    load();</script></body></html>"""
