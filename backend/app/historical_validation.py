"""Strict OHLCV dataset checks for educational historical research.

Input rows must contain timezone-aware ISO timestamps and OHLCV values.
This module validates provenance-neutral data; it does not certify that a
dataset is authentic, licensed, complete, or representative of live markets.
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
from typing import Any


_REQUIRED = ("timestamp", "open", "high", "low", "close", "volume")


def _timestamp(value: Any, row_number: int) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"row {row_number}: timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"row {row_number}: invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"row {row_number}: timestamp must include a timezone")
    return parsed


def validate_ohlcv_rows(rows: list[dict[str, Any]], interval_seconds: int | None = None) -> dict:
    """Validate chronological OHLCV rows and report gaps without fabricating data."""
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError("at least two OHLCV rows are required")
    if interval_seconds is not None and (not isinstance(interval_seconds, int) or interval_seconds <= 0):
        raise ValueError("interval_seconds must be a positive integer")

    parsed_times: list[datetime] = []
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"row {idx}: each row must be an object")
        missing = [key for key in _REQUIRED if key not in row]
        if missing:
            raise ValueError(f"row {idx}: missing fields: {', '.join(missing)}")
        parsed_times.append(_timestamp(row["timestamp"], idx))
        values: dict[str, float] = {}
        for key in ("open", "high", "low", "close", "volume"):
            try:
                value = float(row[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"row {idx}: {key} must be numeric") from exc
            if not isfinite(value):
                raise ValueError(f"row {idx}: {key} must be finite")
            values[key] = value
        if any(values[k] <= 0 for k in ("open", "high", "low", "close")):
            raise ValueError(f"row {idx}: OHLC prices must be positive")
        if values["volume"] < 0:
            raise ValueError(f"row {idx}: volume cannot be negative")
        if values["low"] > min(values["open"], values["close"]) or values["high"] < max(values["open"], values["close"]) or values["low"] > values["high"]:
            raise ValueError(f"row {idx}: invalid OHLC candle geometry")

    duplicate_count = 0
    gaps: list[dict] = []
    for idx in range(1, len(parsed_times)):
        delta = (parsed_times[idx] - parsed_times[idx - 1]).total_seconds()
        if delta == 0:
            duplicate_count += 1
            raise ValueError(f"row {idx + 1}: duplicate timestamp")
        if delta < 0:
            raise ValueError(f"row {idx + 1}: timestamps must be strictly increasing")
        if interval_seconds is not None and delta > interval_seconds:
            missing_intervals = max(0, int(delta // interval_seconds) - 1)
            if missing_intervals:
                gaps.append({
                    "after_row": idx,
                    "before_row": idx + 1,
                    "elapsed_seconds": int(delta),
                    "estimated_missing_intervals": missing_intervals,
                })

    return {
        "valid": True,
        "rows": len(rows),
        "timezone_aware": True,
        "strictly_increasing": True,
        "duplicate_timestamps": duplicate_count,
        "gap_count": len(gaps),
        "gaps": gaps,
        "interval_seconds_checked": interval_seconds,
        "source_authenticity": "NOT_VERIFIED",
        "licensing_status": "NOT_VERIFIED",
        "classification": "DATASET_STRUCTURE_VALIDATION_ONLY",
        "real_orders_enabled": False,
        "paper_only": True,
    }
