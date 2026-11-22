"""CSV historical research supporting OHLC and OHLCV, without imputing volume."""
from __future__ import annotations
import csv, io
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

def _parse_timestamp(value: str, row_number: int) -> tuple[str, bool]:
    raw = (value or "").strip()
    if not raw: raise ValueError(f"row {row_number}: Date is empty")
    try: parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc: raise ValueError(f"row {row_number}: Date must be ISO-8601 (YYYY-MM-DD) or timezone-aware ISO timestamp") from exc
    date_only = len(raw) == 10 and raw[4:5] == "-" and raw[7:8] == "-"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not date_only: raise ValueError(f"row {row_number}: timestamp must include a timezone offset")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(), date_only

def analyze_historical_csv(csv_text: str) -> dict[str, Any]:
    if not isinstance(csv_text, str) or not csv_text.strip(): raise ValueError("CSV content is empty")
    if len(csv_text.encode("utf-8")) > _MAX_BYTES: raise ValueError("CSV exceeds 2 MB limit")
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\\ufeff")))
    if not reader.fieldnames: raise ValueError("CSV header is missing")
    normalized = {}
    for original in reader.fieldnames:
        if original is None: continue
        key = original.strip().lower().replace("_", "").replace(" ", "")
        if key in normalized: raise ValueError(f"duplicate CSV column: {key}")
        normalized[key] = original
    missing = [name for name in _REQUIRED if name not in normalized]
    if missing: raise ValueError("missing required columns: " + ", ".join(missing))
    has_volume = "volume" in normalized
    rows, date_only_count = [], 0
    for row_number, raw in enumerate(reader, start=2):
        if len(rows) >= _MAX_ROWS: raise ValueError(f"CSV exceeds {_MAX_ROWS} data rows")
        timestamp, date_only = _parse_timestamp(raw.get(normalized["date"], ""), row_number)
        date_only_count += int(date_only)
        values = {}
        for field in ("open", "high", "low", "close") + (("volume",) if has_volume else ()):
            text = (raw.get(normalized[field]) or "").strip().replace(",", "")
            try: number = float(text)
            except ValueError as exc: raise ValueError(f"row {row_number}: {field} must be numeric") from exc
            if not isfinite(number): raise ValueError(f"row {row_number}: {field} must be finite")
            values[field] = number
        if any(values[k] <= 0 for k in ("open","high","low","close")):
            raise ValueError(f"row {row_number}: OHLC prices must be positive")
        if values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]) or values["low"] > values["high"]:
            raise ValueError(f"row {row_number}: invalid OHLC candle geometry")
        if has_volume and values["volume"] < 0: raise ValueError(f"row {row_number}: volume cannot be negative")
        rows.append({"timestamp": timestamp, **values})
    if len(rows) < _MIN_ROWS: raise ValueError(f"at least {_MIN_ROWS} valid OHLC rows are required; found {len(rows)}")
    times = [datetime.fromisoformat(r["timestamp"]) for r in rows]
    for i in range(1, len(times)):
        if times[i] == times[i-1]: raise ValueError(f"row {i+2}: duplicate timestamp")
        if times[i] < times[i-1]: raise ValueError(f"row {i+2}: dates must be in chronological order (oldest to newest)")
    highs, lows, closes = [r["high"] for r in rows], [r["low"] for r in rows], [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows] if has_volume else None
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
        "engine": "V6_2_HISTORICAL_CSV_RESEARCH",
        "classification": "DESCRIPTIVE_HISTORICAL_RESEARCH_ONLY",
        "data_basis": "USER_SUPPLIED_HISTORICAL_OHLCV" if has_volume else "USER_SUPPLIED_HISTORICAL_OHLC",
        "volume_available": has_volume, "rows": len(rows),
        "source_authenticity": "NOT_VERIFIED", "licensing_status": "NOT_VERIFIED",
        "first_timestamp": rows[0]["timestamp"], "last_timestamp": rows[-1]["timestamp"],
        "date_only_rows_normalized_to_utc_midnight": date_only_count,
        "dataset_validation": validation, "market_context": context,
        "multi_factor": factors, "walk_forward": walk,
        "limitations": [
            "CSV structure validation does not authenticate exchange origin or licensing.",
            "Date-only daily bars are represented at UTC midnight for ordering; no intraday time is inferred.",
            "No missing observations or volume values are fabricated.",
            "Volume-dependent metrics such as VWAP and volume factor are unavailable when Volume is absent.",
            "Walk-forward metrics are a descriptive EMA baseline, not an executable strategy.",
            "Fees, slippage, liquidity and market impact are not modelled.",
            "No predictive probability, BUY/SELL instruction or real order is produced.",
        ],
        "is_trade_signal": False, "real_orders_enabled": False, "paper_only": True,
    }
