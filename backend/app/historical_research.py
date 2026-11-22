"""CSV historical research supporting OHLC and OHLCV, without imputing volume."""
from __future__ import annotations
import csv, io, re
from datetime import datetime, timezone
from math import isfinite
from typing import Any
from .advanced_analysis import analyze_market_context
from .historical_validation import validate_ohlcv_rows
from .multifactor import analyze_factors
from .walk_forward import evaluate_walk_forward

_REQUIRED = ("date", "open", "high", "low", "close")
_MAX_BYTES = 2_000_000
_MAX_ROWS = 20_000
_MIN_ROWS = 50

def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").replace("\ufeff", "").strip().lower())

def _date_matches(value: str, pattern: str) -> bool:
    try:
        datetime.strptime(value, pattern)
        return True
    except ValueError:
        return False

def _parse_timestamp(value: str, row_number: int) -> tuple[str, bool]:
    raw = (value or "").strip().strip('"')
    if not raw: raise ValueError(f"row {row_number}: Date is empty")
    date_formats = ("%Y-%m-%d", "%d %b %Y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y")
    parsed = None
    for pattern in date_formats:
        try:
            parsed = datetime.strptime(raw, pattern)
            break
        except ValueError:
            pass
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"row {row_number}: unsupported Date format '{raw}'") from exc
    date_only = parsed.tzinfo is None and (
        (len(raw) == 10 and raw[4:5] == "-" and raw[7:8] == "-")
        or any(_date_matches(raw, pattern) for pattern in ("%d %b %Y", "%d-%b-%Y", "%d-%m-%Y", "%d/%m/%Y"))
    )
    if parsed.tzinfo is None:
        if not date_only:
            raise ValueError(f"row {row_number}: timestamp must include a timezone offset")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(), date_only

def analyze_historical_csv(csv_text: str) -> dict[str, Any]:
    if not isinstance(csv_text, str) or not csv_text.strip(): raise ValueError("CSV content is empty")
    if len(csv_text.encode("utf-8")) > _MAX_BYTES: raise ValueError("CSV exceeds 2 MB limit")
    lines = [line for line in csv_text.lstrip("\ufeff").splitlines() if line.strip()]
    if len(lines) < 2: raise ValueError("CSV needs a header and at least 50 data rows")
    header_index = -1
    aliases = {
        "date": {"date", "indexdate", "tradedate"},
        "open": {"open", "openindexvalue", "openprice"},
        "high": {"high", "highindexvalue", "highprice"},
        "low": {"low", "lowindexvalue", "lowprice"},
        "close": {"close", "closingindexvalue", "closeindexvalue", "closingprice"},
        "volume": {"volume", "tradedquantity", "totaltradedquantity", "totalvolume"},
    }
    for i, line in enumerate(lines):
        try: candidate = next(csv.reader([line]))
        except csv.Error: continue
        keys = {_normalize_header(x) for x in candidate}
        if all(keys & aliases[k] for k in ("date","open","high","low","close")):
            header_index = i
            break
    if header_index < 0:
        raise ValueError("NSE CSV header not recognised. Expected Date/Open/High/Low/Close or NSE Index Value headings.")
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])))
    if not reader.fieldnames: raise ValueError("CSV header is missing")
    normalized: dict[str, str] = {}
    for original in reader.fieldnames:
        if original is None: continue
        key = _normalize_header(original)
        if key in normalized: raise ValueError(f"duplicate CSV column: {key}")
        normalized[key] = original
    chosen = {}
    for field in ("date","open","high","low","close","volume"):
        matches = [key for key in normalized if key in aliases[field]]
        if matches: chosen[field] = normalized[matches[0]]
    rows, date_only_count = [], 0
    for row_number, raw in enumerate(reader, start=header_index+2):
        if len(rows) >= _MAX_ROWS: raise ValueError(f"CSV exceeds {_MAX_ROWS} data rows")
        timestamp, date_only = _parse_timestamp(raw.get(chosen["date"], ""), row_number)
        date_only_count += int(date_only)
        values = {}
        fields = ("open","high","low","close") + (("volume",) if "volume" in chosen else ())
        for field in fields:
            text = (raw.get(chosen[field]) or "").strip().replace(",", "")
            try: number = float(text)
            except ValueError as exc: raise ValueError(f"row {row_number}: {field} must be numeric") from exc
            if not isfinite(number): raise ValueError(f"row {row_number}: {field} must be finite")
            values[field] = number
        if any(values[k] <= 0 for k in ("open","high","low","close")):
            raise ValueError(f"row {row_number}: OHLC prices must be positive")
        if values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]) or values["low"] > values["high"]:
            raise ValueError(f"row {row_number}: invalid OHLC candle geometry")
        if "volume" in values and values["volume"] < 0: raise ValueError(f"row {row_number}: volume cannot be negative")
        rows.append({"timestamp": timestamp, **values})
    if len(rows) < _MIN_ROWS: raise ValueError(f"at least {_MIN_ROWS} valid OHLC rows are required; found {len(rows)}")
    # NSE historical index reports commonly arrive newest-first. Normalize ordering.
    rows.sort(key=lambda row: row["timestamp"])
    times = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    for i in range(1, len(times)):
        if times[i] == times[i-1]: raise ValueError(f"duplicate date at normalized row {i+1}")
    highs, lows, closes = [r["high"] for r in rows], [r["low"] for r in rows], [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows] if "volume" in chosen else None
    factors = analyze_factors(highs, lows, closes, volumes)
    walk = evaluate_walk_forward(closes, min_history=30)
    context = analyze_market_context(highs, lows, closes, volumes)
    validation = {
        "valid": True, "rows": len(rows), "timezone_aware": True,
        "strictly_increasing": True, "duplicate_timestamps": 0,
        "gap_count": 0, "gaps": [], "interval_seconds_checked": None,
        "source_authenticity": "NOT_VERIFIED", "licensing_status": "NOT_VERIFIED",
        "classification": "DATASET_STRUCTURE_VALIDATION_ONLY",
        "real_orders_enabled": False, "paper_only": True,
    }
    return {
        "engine": "V6_3_NSE_NATIVE_CSV_RESEARCH",
        "classification": "DESCRIPTIVE_HISTORICAL_RESEARCH_ONLY",
        "data_basis": "USER_SUPPLIED_HISTORICAL_OHLCV" if volumes is not None else "USER_SUPPLIED_HISTORICAL_OHLC",
        "volume_available": volumes is not None, "rows": len(rows),
        "source_authenticity": "NOT_VERIFIED", "licensing_status": "NOT_VERIFIED",
        "input_order_normalized": "NEWEST_FIRST_OR_MIXED_INPUT_SORTED_CHRONOLOGICALLY",
        "first_timestamp": rows[0]["timestamp"], "last_timestamp": rows[-1]["timestamp"],
        "date_only_rows_normalized_to_utc_midnight": date_only_count,
        "dataset_validation": validation, "market_context": context,
        "multi_factor": factors, "walk_forward": walk,
        "limitations": [
            "CSV structure validation does not authenticate exchange origin or licensing.",
            "Date-only daily bars are represented at UTC midnight; no intraday time is inferred.",
            "No missing observations or volume values are fabricated.",
            "Volume-dependent metrics such as VWAP and volume factor are unavailable when Volume is absent.",
            "Walk-forward metrics are descriptive diagnostics, not an executable strategy.",
            "No predictive probability, BUY/SELL instruction or real order is produced.",
        ],
        "is_trade_signal": False, "real_orders_enabled": False, "paper_only": True,
    }
