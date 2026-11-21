"""Market-data freshness and validation helpers."""
from datetime import datetime, timezone
from math import isfinite

def validate_quote(symbol: str, price: float, timestamp: datetime) -> dict:
    if not symbol or not isinstance(symbol, str):
        raise ValueError("symbol is required")
    if not isfinite(float(price)) or float(price) <= 0:
        raise ValueError("price must be finite and positive")
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    age_seconds = max(0.0, (datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds())
    return {
        "symbol": symbol,
        "price": float(price),
        "timestamp": timestamp.isoformat(),
        "age_seconds": round(age_seconds, 1),
        "fresh": age_seconds <= 15,
        "status": "FRESH" if age_seconds <= 15 else "STALE",
    }
