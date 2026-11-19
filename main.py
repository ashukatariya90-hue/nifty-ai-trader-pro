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

app = FastAPI(title="NIFTY AI TRADER PRO — V5.13 Catalogue Management", version="5.13.0")
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

@app.get("/api/health")
async def health():
    return {"status":"ok","version":"5.13.0","mode":"EDUCATIONAL_PAPER_ONLY",
            "real_orders_enabled":False,"virtual_capital":500000}

@app.get("/api/v5/integration-status")
async def integration_status():
    return {"app_version":"5.13.0","integration_foundation":"READ_ONLY_CATALOGUE_MANAGEMENT",
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
    # Replace atomically only after the entire new catalogue passes validation.
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
    return """<html><body><h2>NIFTY AI TRADER PRO V5.13</h2>
    <p>Educational paper mode. No live feed or real orders.</p>
    <p>Catalogue endpoints: GET summary, GET instruments, POST import, DELETE clear.</p>
    </body></html>"""
