"""CSV-to-research pipeline for educational historical OHLCV datasets.

The pipeline validates structure and computes descriptive factors plus a
chronological next-bar baseline. It never authenticates source provenance or
creates trading instructions.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from .advanced_analysis import analyze_market_context
from .historical_validation import validate_ohlcv_rows
from .multifactor import analyze_factors
from .walk_forward import evaluate_walk_forward

_REQUIRED = ("date", "open", "high", "low", "close", "volume")
_MAX_BYTES = 2_000_000
_MAX_ROWS = 20_000
_MIN_ROWS = 50


def _parse_timestamp(value: str, row_number: int) -> tuple[str, bool]:
    raw = (value or "").strip()
    if not raw:
        raise ValueError(f"row {row_number}: Date is empty")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"row {row_number}: Date must be ISO-8601") from exc
    date_only = len(raw) == 10 and raw[4:5] == "-" and raw[7:8] == "-"
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not date_only:
            raise ValueError(f"row {row_number}: timestamp must include a timezone offset")
        # Date-only daily bars are represented at UTC midnight for ordering only.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(), date_only


def analyze_historical_csv(csv_text: str) -> dict[str, Any]:
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("CSV content is empty")
    if len(csv_text.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("CSV exceeds 2 MB limit")

    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV header is missing")
    normalized: dict[str, str] = {}
    for original in reader.fieldnames:
        if original is None:
            continue
        key = original.strip().lower().replace("_", "").replace(" ", "")
        if key in normalized:
            raise ValueError(f"duplicate CSV column: {key}")
        normalized[key] = original
    missing = [name for name in _REQUIRED if name not in normalized]
    if missing:
        raise ValueError("missing required columns: " + ", ".join(missing))

    rows: list[dict[str, Any]] = []
    date_only_count = 0
    for row_number, raw in enumerate(reader, start=2):
        if len(rows) >= _MAX_ROWS:
            raise ValueError(f"CSV exceeds {_MAX_ROWS} data rows")
        timestamp, was_date_only = _parse_timestamp(raw.get(normalized["date"], ""), row_number)
        date_only_count += int(was_date_only)
        values: dict[str, float] = {}
        for field in _REQUIRED[1:]:
            text = (raw.get(normalized[field]) or "").strip().replace(",", "")
            try:
                number = float(text)
            except ValueError as exc:
                raise ValueError(f"row {row_number}: {field} must be numeric") from exc
            if not isfinite(number):
                raise ValueError(f"row {row_number}: {field} must be finite")
            values[field] = number
        rows.append({"timestamp": timestamp, **values})

    if len(rows) < _MIN_ROWS:
        raise ValueError(f"at least {_MIN_ROWS} valid OHLCV rows are required; found {len(rows)}")

    validation = validate_ohlcv_rows(rows)
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    closes = [r["close"] for r in rows]
    volumes = [r["volume"] for r in rows]

    factors = analyze_factors(highs, lows, closes, volumes)
    walk_forward = evaluate_walk_forward(closes, min_history=30)
    market_context = analyze_market_context(highs, lows, closes, volumes)

    return {
        "engine": "V6_1_HISTORICAL_CSV_RESEARCH",
        "classification": "DESCRIPTIVE_HISTORICAL_RESEARCH_ONLY",
        "data_basis": "USER_SUPPLIED_HISTORICAL_CSV",
        "source_authenticity": "NOT_VERIFIED",
        "licensing_status": "NOT_VERIFIED",
        "rows": len(rows),
        "first_timestamp": rows[0]["timestamp"],
        "last_timestamp": rows[-1]["timestamp"],
        "date_only_rows_normalized_to_utc_midnight": date_only_count,
        "dataset_validation": validation,
        "market_context": market_context,
        "multi_factor": factors,
        "walk_forward": walk_forward,
        "limitations": [
            "CSV structure validation does not authenticate exchange origin or licensing.",
            "Date-only daily bars are represented at UTC midnight for ordering; no intraday time is inferred.",
            "No missing observations are fabricated or filled.",
            "Walk-forward metrics are a descriptive EMA baseline, not an executable strategy.",
            "Fees, slippage, liquidity and market impact are not modelled.",
            "No predictive probability, BUY/SELL instruction or real order is produced.",
        ],
        "is_trade_signal": False,
        "real_orders_enabled": False,
        "paper_only": True,
    }
