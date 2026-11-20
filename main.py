from datetime import datetime, timezone
from math import isfinite
from typing import Optional
import csv
import io
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from paper import PaperLedger
from analysis import analyze_closes, ema_crossover_backtest
from angel_one import AngelOneMarketDataAdapter

app = FastAPI(title="NIFTY AI TRADER PRO — V5.14 Early Momentum Engine", version="5.14.0")
ledger = PaperLedger(500000)
angel = AngelOneMarketDataAdapter()

INDEX_UNIVERSE = [
    {"symbol":"NIFTY","name":"NIFTY 50","exchange":"NSE"},
    {"symbol":"BANKNIFTY","name":"NIFTY BANK","exchange":"NSE"},
    {"symbol":"FINNIFTY","name":"NIFTY FINANCIAL SERVICES","exchange":"NSE"},
    {"symbol":"MIDCPNIFTY","name":"NIFTY MIDCAP SELECT","exchange":"NSE"},
    {"symbol":"SENSEX","name":"S&P BSE SENSEX","exchange":"BSE"},
    {"symbol":"BANKEX","name":"BSE BANKEX","exchange":"BSE"},
]
REQUIRED = {"symbol","exchange","segment","instrument_token","expiry","strike","option_type"}
MAX_ROWS = 50000
MAX_BODY_BYTES = 20_000_000
catalogue: list[dict] = []
catalogue_loaded_at: Optional[str] = None
catalogue_source: Optional[str] = None
clients: set[WebSocket] = set()
latest_event: Optional[dict] = None

class CloseSeries(BaseModel):
    close_prices: list[float] = Field(min_length=1, max_length=10000)

class BacktestRequest(BaseModel):
    close_prices: list[float] = Field(min_length=30, max_length=10000)
    fee_bps: float = Field(default=5.0, ge=0, le=100)

class PaperOrder(BaseModel):
    side: str
    quantity: int = Field(gt=0, le=100000)
    reference_price: float = Field(gt=0)

class Candle5m(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

class EarlyMomentumRequest(BaseModel):
    symbol: str = Field(default="NIFTY", min_length=1, max_length=40)
    candles: list[Candle5m] = Field(min_length=3, max_length=100)
    previous_close: Optional[float] = Field(default=None, gt=0)
    # Baseline is volume for the same elapsed market-time window, not a full-day average.
    average_volume_same_window: Optional[float] = Field(default=None, gt=0)
    advance_decline_ratio: Optional[float] = Field(default=None, gt=0)
    pcr: Optional[float] = Field(default=None, gt=0, le=5)
    pcr_change: Optional[float] = None
    # News sentiment is a normalized, timestamped provider score in [-1, 1].
    news_sentiment: Optional[float] = Field(default=None, ge=-1, le=1)
    news_timestamp: Optional[datetime] = None
    # FII net flow is daily context (₹ crore); never treated as a first-20-minute live trigger.
    fii_net_flow_daily_cr: Optional[float] = None
    india_vix: Optional[float] = Field(default=None, gt=0)
    data_source: str = Field(default="USER_SUPPLIED", max_length=80)
    data_timestamp: Optional[datetime] = None

def normalize_record(raw: dict, source: str) -> dict:
    aliases = {
        "symbol": ("symbol", "tradingsymbol", "trading_symbol"),
        "exchange": ("exchange", "exch_seg", "exchange_segment"),
        "segment": ("segment", "instrumenttype", "instrument_type"),
        "instrument_token": ("instrument_token", "token"),
        "expiry": ("expiry",),
        "strike": ("strike",),
        "option_type": ("option_type", "optionType"),
    }
    result = {}
    for target, names in aliases.items():
        value = next((raw.get(n) for n in names if raw.get(n) is not None), "")
        result[target] = str(value).strip()
    result["symbol"] = result["symbol"].upper()
    result["exchange"] = result["exchange"].upper()
    result["segment"] = result["segment"].upper()
    result["option_type"] = result["option_type"].upper()

    if not result["option_type"] and result["symbol"].endswith("CE"):
        result["option_type"] = "CE"
    elif not result["option_type"] and result["symbol"].endswith("PE"):
        result["option_type"] = "PE"

    if result["option_type"] not in {"", "CE", "PE"}:
        raise ValueError("option_type must be CE or PE")
    token = result["instrument_token"]
    if not result["symbol"] or not token.isdigit() or int(token) <= 0:
        raise ValueError("symbol and positive numeric instrument token are required")
    if result["exchange"] not in {"NSE", "BSE", "NFO", "BFO"}:
        raise ValueError("unsupported exchange value")
    if not result["segment"]:
        raise ValueError("segment/instrumenttype is required")
    try:
        strike = float(result["strike"] or 0)
        if not isfinite(strike) or strike < 0:
            raise ValueError()
    except Exception:
        raise ValueError("invalid strike")
    result["strike"] = str(strike)
    if result["option_type"] and (not result["expiry"] or strike <= 0):
        raise ValueError("option records require expiry and positive strike")
    return result

def summarize(rows):
    by_exchange, by_segment, by_symbol = {}, {}, {}
    sides = {"CE": 0, "PE": 0}
    for row in rows:
        for target, key in ((by_exchange, "exchange"), (by_segment, "segment"), (by_symbol, "symbol")):
            target[row[key]] = target.get(row[key], 0) + 1
        if row["option_type"] in sides:
            sides[row["option_type"]] += 1
    return {
        "total": len(rows),
        "by_exchange": by_exchange,
        "by_segment": by_segment,
        "by_symbol": by_symbol,
        "option_sides": sides,
    }

def validate_rows(rows):
    if not rows:
        raise HTTPException(400, "Instrument Master contains no records")
    if len(rows) > MAX_ROWS:
        raise HTTPException(413, "Too many instrument records")
    seen_tokens, seen_contracts = set(), set()
    for i, row in enumerate(rows, start=1):
        token_key = (row["exchange"], row["instrument_token"])
        contract_key = tuple(row[k] for k in ("exchange", "segment", "symbol", "expiry", "strike", "option_type"))
        if token_key in seen_tokens:
            raise HTTPException(400, f"Duplicate exchange/token at record {i}")
        if contract_key in seen_contracts:
            raise HTTPException(400, f"Duplicate contract at record {i}")
        seen_tokens.add(token_key)
        seen_contracts.add(contract_key)
    return rows

def parse_catalogue_body(body: str):
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise HTTPException(413, "Payload exceeds 20 MB")
    rows = []
    stripped = body.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            raise HTTPException(400, f"Invalid JSON: {exc.msg}")
        if isinstance(payload, dict):
            payload = payload.get("data", payload.get("instruments"))
        if not isinstance(payload, list):
            raise HTTPException(400, "JSON must be an array or contain data/instruments array")
        if len(payload) > MAX_ROWS:
            raise HTTPException(413, "Too many instrument records")
        for idx, raw in enumerate(payload, start=1):
            if not isinstance(raw, dict):
                raise HTTPException(400, f"JSON record {idx} is not an object")
            try:
                rows.append(normalize_record(raw, "json"))
            except ValueError as exc:
                raise HTTPException(400, f"JSON record {idx}: {exc}")
        source = "USER_SUPPLIED_JSON"
    else:
        reader = csv.DictReader(io.StringIO(body))
        missing = sorted(REQUIRED - set(reader.fieldnames or []))
        if missing:
            raise HTTPException(400, {"error": "missing_required_columns", "missing": missing})
        for idx, raw in enumerate(reader, start=2):
            try:
                rows.append(normalize_record(raw, "csv"))
            except ValueError as exc:
                raise HTTPException(400, f"CSV line {idx}: {exc}")
        source = "USER_SUPPLIED_CSV"
    validate_rows(rows)
    return rows, source

def _ema(values: list[float], period: int) -> float:
    alpha = 2.0 / (period + 1.0)
    value = values[0]
    for item in values[1:]:
        value = alpha * item + (1.0 - alpha) * value
    return value

def _rsi(values: list[float], period: int = 7) -> Optional[float]:
    if len(values) < period + 1:
        return None
    changes = [values[i] - values[i-1] for i in range(len(values)-period, len(values))]
    gains = sum(max(x, 0.0) for x in changes) / period
    losses = sum(max(-x, 0.0) for x in changes) / period
    if losses == 0:
        return 100.0 if gains > 0 else 50.0
    return 100.0 - (100.0 / (1.0 + gains / losses))

def _aware_age_seconds(ts: Optional[datetime]) -> Optional[float]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        raise HTTPException(400, "All timestamps must include timezone")
    return max(0.0, (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds())

def early_momentum_analysis(data: EarlyMomentumRequest) -> dict:
    candles = sorted(data.candles, key=lambda c: c.timestamp)
    if any(c.timestamp.tzinfo is None for c in candles):
        raise HTTPException(400, "Candle timestamps must include timezone")
    if any(c.high < max(c.open, c.close, c.low) or c.low > min(c.open, c.close) for c in candles):
        raise HTTPException(400, "Invalid OHLC candle range")
    if len({c.timestamp for c in candles}) != len(candles):
        raise HTTPException(400, "Duplicate candle timestamps")
    closes = [c.close for c in candles]
    volumes = [c.volume for c in candles]
    first_ts, last_ts = candles[0].timestamp, candles[-1].timestamp
    elapsed_minutes = max(0.0, (last_ts-first_ts).total_seconds()/60.0 + 5.0)
    if elapsed_minutes > 45:
        phase = "LATER_INTRADAY_REPLAY"
    elif elapsed_minutes >= 15:
        phase = "OPENING_15_20_MIN_WINDOW"
    else:
        phase = "EARLY_INSUFFICIENT_WINDOW"

    components = {}
    reasons = []
    # Short EMA pair is deliberately used for the opening window; it is not a full-session trend.
    ema_fast, ema_slow = _ema(closes[-min(3, len(closes)):], 3), _ema(closes[-min(6, len(closes)):], 6)
    components["short_ema_alignment"] = 1 if ema_fast > ema_slow else (-1 if ema_fast < ema_slow else 0)
    reasons.append(f"Short EMA3/EMA6: {'positive' if ema_fast > ema_slow else 'negative' if ema_fast < ema_slow else 'flat'}")

    typical = [(c.high+c.low+c.close)/3.0 for c in candles]
    total_vol = sum(volumes)
    vwap = (sum(t*v for t,v in zip(typical,volumes))/total_vol) if total_vol > 0 else None
    components["vwap_position"] = (1 if closes[-1] > vwap else -1 if closes[-1] < vwap else 0) if vwap else None
    if vwap:
        reasons.append("Latest close is above VWAP" if closes[-1] > vwap else "Latest close is below VWAP" if closes[-1] < vwap else "Latest close is at VWAP")

    opening_high = max(c.high for c in candles[:3])
    opening_low = min(c.low for c in candles[:3])
    if len(candles) > 3 and closes[-1] > opening_high:
        breakout = 1
    elif len(candles) > 3 and closes[-1] < opening_low:
        breakout = -1
    else:
        breakout = 0
    components["opening_range_break"] = breakout
    reasons.append("Close above initial range" if breakout > 0 else "Close below initial range" if breakout < 0 else "No confirmed initial-range break")

    rsi = _rsi(closes, 7)
    components["rsi_momentum"] = (1 if 52 <= rsi <= 72 else -1 if 28 <= rsi <= 48 else 0) if rsi is not None else None
    if rsi is not None:
        reasons.append(f"RSI(7)={rsi:.1f}")

    rel_volume = None
    if data.average_volume_same_window:
        rel_volume = total_vol / data.average_volume_same_window
        # Volume confirms the direction already present in price; volume alone has no direction.
        price_direction = 1 if closes[-1] > closes[0] else (-1 if closes[-1] < closes[0] else 0)
        components["relative_volume_confirmation"] = price_direction if rel_volume >= 1.2 else 0
        reasons.append(f"Relative volume={rel_volume:.2f}x same-window baseline")
    else:
        components["relative_volume_confirmation"] = None
        reasons.append("Same-window volume baseline missing")

    if data.advance_decline_ratio is not None:
        components["market_breadth"] = 1 if data.advance_decline_ratio > 1.15 else (-1 if data.advance_decline_ratio < 0.87 else 0)
        reasons.append(f"Advance/decline ratio={data.advance_decline_ratio:.2f}")
    else:
        components["market_breadth"] = None

    if data.pcr is not None:
        # PCR is weak context, not a directional trigger by itself.
        pcr_score = 1 if 0.9 <= data.pcr <= 1.3 else (-1 if data.pcr < 0.7 or data.pcr > 1.8 else 0)
        components["options_pcr_context"] = pcr_score
        reasons.append(f"PCR={data.pcr:.2f} (context only)")
    else:
        components["options_pcr_context"] = None

    if data.pcr_change is not None:
        components["pcr_change_context"] = 1 if data.pcr_change > 0.05 else (-1 if data.pcr_change < -0.05 else 0)
    else:
        components["pcr_change_context"] = None

    if data.news_sentiment is not None:
        components["news_sentiment_context"] = 1 if data.news_sentiment >= 0.25 else (-1 if data.news_sentiment <= -0.25 else 0)
        age = _aware_age_seconds(data.news_timestamp)
        if age is None:
            reasons.append("News sentiment supplied without timestamp; freshness cannot be verified")
        else:
            reasons.append(f"News sentiment timestamp age={age:.0f}s")
    else:
        components["news_sentiment_context"] = None

    if data.india_vix is not None:
        reasons.append(f"India VIX={data.india_vix:.2f}; volatility context only")
    if data.fii_net_flow_daily_cr is not None:
        reasons.append(f"FII daily net flow ₹{data.fii_net_flow_daily_cr:.0f} crore; daily context only, not an opening trigger")

    weights = {
        "short_ema_alignment": 20, "vwap_position": 20, "opening_range_break": 20,
        "rsi_momentum": 10, "relative_volume_confirmation": 15, "market_breadth": 5,
        "options_pcr_context": 4, "pcr_change_context": 2, "news_sentiment_context": 4,
    }
    available = [(weights[k], v) for k,v in components.items() if v is not None]
    total_weight = sum(w for w,_ in available)
    score = (sum(w*v for w,v in available)/total_weight*100.0) if total_weight else 0.0
    if len(candles) < 4 or elapsed_minutes < 15:
        classification = "EARLY_INSUFFICIENT_WINDOW"
    elif total_weight < 65:
        classification = "INSUFFICIENT_DATA_COVERAGE"
    elif score >= 45 and components.get("relative_volume_confirmation") != -1:
        classification = "BULLISH_MOMENTUM_WATCH"
    elif score <= -45:
        classification = "BEARISH_MOMENTUM_WATCH"
    else:
        classification = "MIXED_OR_UNCONFIRMED"

    return {
        "symbol": data.symbol.upper(),
        "classification": classification,
        "score": round(score, 1),
        "available_weight_pct": round(total_weight, 1),
        "opening_phase": phase,
        "candles_used": len(candles),
        "last_completed_candle_at": last_ts.isoformat(),
        "last_close": closes[-1],
        "vwap": round(vwap, 2) if vwap is not None else None,
        "ema3": round(ema_fast, 2),
        "ema6": round(ema_slow, 2),
        "rsi7": round(rsi, 2) if rsi is not None else None,
        "relative_volume": round(rel_volume, 2) if rel_volume is not None else None,
        "components": components,
        "reasons": reasons,
        "missing_inputs": [k for k,v in components.items() if v is None],
        "data_source": data.data_source,
        "data_timestamp_age_seconds": _aware_age_seconds(data.data_timestamp),
        "live_data_verified": False,
        "real_orders_enabled": False,
        "mode": "EDUCATIONAL_PAPER_ONLY",
        "disclaimer": "Momentum classification for historical/paper research only; not a BUY/SELL instruction or guarantee. Supplied data source and freshness are not independently verified."
    }

@app.get("/api/health")
async def health():
    return {"status":"ok","version":"5.14.0","mode":"EDUCATIONAL_PAPER_ONLY",
            "real_orders_enabled":False,"virtual_capital":500000}

@app.get("/api/v5/integration-status")
async def integration_status():
    return {"app_version":"5.14.0","integration_foundation":"READ_ONLY_CATALOGUE_AND_EARLY_MOMENTUM",
            "angel_one":await angel.status(),"catalogue_loaded":bool(catalogue),
            "catalogue_count":len(catalogue),"catalogue_loaded_at":catalogue_loaded_at,
            "stream":{"endpoint":"/ws/market","status":"HISTORICAL_REPLAY_ONLY",
                      "connected_clients":len(clients)},
            "supported_indices":[x["symbol"] for x in INDEX_UNIVERSE],
            "live_data_verified":False,"real_orders_enabled":False,
            "mode":"EDUCATIONAL_PAPER_ONLY"}

@app.get("/api/providers/angel-one")
async def provider_status():
    return await angel.status()

@app.get("/api/market/universe")
async def market_universe():
    return {"status":"CATALOGUE_TARGETS_ONLY","live_data":False,"indices":INDEX_UNIVERSE,
            "instrument_master":{"loaded":bool(catalogue),"count":len(catalogue),
                                 "loaded_at":catalogue_loaded_at,"source":catalogue_source},
            "note":"Index targets are not proof of listed/available contracts."}

@app.post("/api/market/instrument-master")
async def load_instrument_master(body: str = Body(..., media_type="text/plain")):
    global catalogue, catalogue_loaded_at, catalogue_source
    rows, source = parse_catalogue_body(body)
    catalogue = rows
    catalogue_loaded_at = datetime.now(timezone.utc).isoformat()
    catalogue_source = source
    return {"status":"LOADED","count":len(rows),"loaded_at":catalogue_loaded_at,
            "summary":summarize(rows),"source":source,"live_data":False,
            "exchange_token_verification":"FORMAT_AND_DUPLICATE_CHECK_ONLY",
            "note":"Catalogue metadata only; no broker connection or live quote verification."}

@app.delete("/api/market/instrument-master")
async def clear_instrument_master():
    global catalogue, catalogue_loaded_at, catalogue_source
    removed = len(catalogue)
    catalogue = []
    catalogue_loaded_at = None
    catalogue_source = None
    return {"status":"CLEARED","removed_records":removed,"count":0,
            "live_data":False,"note":"In-memory catalogue cleared; it will also be empty after a server restart."}

@app.get("/api/market/instrument-master/summary")
async def instrument_master_summary():
    return {"loaded":bool(catalogue),"count":len(catalogue),"loaded_at":catalogue_loaded_at,
            "summary":summarize(catalogue) if catalogue else {},
            "source":catalogue_source or "NONE","live_data":False,
            "exchange_token_verification":"FORMAT_AND_DUPLICATE_CHECK_ONLY"}

@app.get("/api/market/instruments")
async def list_instruments(
    symbol: Optional[str] = None,
    segment: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
):
    rows = catalogue
    if symbol:
        rows = [r for r in rows if r["symbol"] == symbol.strip().upper()]
    if segment:
        rows = [r for r in rows if r["segment"] == segment.strip().upper()]
    if exchange:
        rows = [r for r in rows if r["exchange"] == exchange.strip().upper()]
    total = len(rows)
    page = rows[offset:offset + limit]
    return {"count":total,"returned":len(page),"limit":limit,"offset":offset,
            "live_data":False,"instruments":page}

@app.get("/api/market/feed-status")
async def feed_status():
    if latest_event:
        return {"status":"HISTORICAL_REPLAY","source":"USER_SUPPLIED_CSV_REPLAY",
                "connected":False,"last_event_at":latest_event["exchange_timestamp"],
                "freshness":"DELAYED","read_only":True,"live_data_verified":False,
                "websocket_clients":len(clients)}
    return {"status":"OFFLINE","source":"NONE","connected":False,"last_event_at":None,
            "freshness":"NO_DATA","read_only":True,"live_data_verified":False,
            "websocket_clients":len(clients)}

@app.post("/api/market/replay-csv")
async def replay_csv(body: str = Body(..., media_type="text/plain")):
    global latest_event
    if len(body.encode("utf-8")) > MAX_BODY_BYTES:
        raise HTTPException(413, "Payload exceeds 20 MB")
    reader = csv.DictReader(io.StringIO(body))
    required = {"symbol","timestamp","last_price"}
    missing = sorted(required - set(reader.fieldnames or []))
    if missing:
        raise HTTPException(400, {"error":"missing_required_columns","missing":missing})
    count = 0
    for idx, row in enumerate(reader, start=2):
        try:
            ts = datetime.fromisoformat(row["timestamp"].strip().replace("Z","+00:00"))
            price = float(row["last_price"])
            if ts.tzinfo is None or not isfinite(price) or price <= 0:
                raise ValueError("invalid timestamp/price")
            latest_event = {"type":"market_event","symbol":row["symbol"].strip().upper(),
                "last_price":price,"exchange_timestamp":ts.isoformat(),
                "source":"USER_SUPPLIED_CSV_REPLAY","mode":"HISTORICAL_REPLAY",
                "delayed":True,"read_only":True,"live_data_verified":False}
            for ws in list(clients):
                try:
                    await ws.send_json(latest_event)
                except Exception:
                    clients.discard(ws)
            count += 1
        except Exception as exc:
            raise HTTPException(400, f"CSV line {idx}: {exc}")
    if count == 0:
        raise HTTPException(400, "No replay rows")
    return {"status":"REPLAY_COMPLETE","rows_replayed":count,
            "live_data_verified":False,"source":"USER_SUPPLIED_CSV_REPLAY"}

@app.websocket("/ws/market")
async def market_ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        await ws.send_json({"type":"status","status":"CONNECTED",
                            "mode":"HISTORICAL_REPLAY_ONLY",
                            "live_data_verified":False,"read_only":True})
        if latest_event:
            await ws.send_json(latest_event)
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)

@app.get("/api/market")
async def market():
    return latest_event or {"symbol":"NIFTY","value":None,"source":"NO_LIVE_FEED",
        "status":"OFFLINE","read_only":True,"live_data_verified":False}

@app.get("/api/market/validate-event")
async def validate_event(symbol: str, last_price: float, exchange_timestamp: datetime):
    if exchange_timestamp.tzinfo is None:
        raise HTTPException(400,"Timestamp must include timezone")
    age = max(0,(datetime.now(timezone.utc)-exchange_timestamp.astimezone(timezone.utc)).total_seconds())
    return {"valid":last_price>0,"symbol":symbol.upper(),"last_price":last_price,
            "age_seconds":round(age,2),"freshness":"FRESH" if age<=15 else "STALE",
            "source":"VALIDATION_ONLY","live_data_verified":False}

@app.post("/api/analysis/indicators")
async def indicators(data: CloseSeries):
    try:
        return analyze_closes(data.close_prices)
    except ValueError as exc:
        raise HTTPException(400,str(exc))

@app.post("/api/analysis/early-momentum")
async def early_momentum(data: EarlyMomentumRequest):
    return early_momentum_analysis(data)

@app.post("/api/backtest/ema-crossover")
async def backtest(data: BacktestRequest):
    try:
        return ema_crossover_backtest(data.close_prices,data.fee_bps)
    except ValueError as exc:
        raise HTTPException(400,str(exc))

@app.get("/api/paper/ledger")
async def paper_ledger():
    return ledger.snapshot()

@app.post("/api/paper/order")
async def paper_order(order: PaperOrder):
    try:
        return ledger.record(order.side,order.quantity,order.reference_price)
    except ValueError as exc:
        raise HTTPException(400,str(exc))

@app.get("/",response_class=HTMLResponse)
async def dashboard():
    return """<html><body><h2>NIFTY AI TRADER PRO V5.14</h2>
    <p>Educational paper mode. No live feed or real orders.</p>
    <p>Catalogue endpoints: GET summary, GET instruments, POST import, DELETE clear.</p>
    <p>Early momentum endpoint: POST /api/analysis/early-momentum (paper research only).</p>
    </body></html>"""
