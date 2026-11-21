"""Read-only normalized market-data event contract and validation."""
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class MarketTick:
    symbol: str
    last_price: float
    exchange_timestamp: datetime
    received_timestamp: datetime
    source: str
    delayed: bool = False

    @property
    def freshness(self) -> str:
        if self.delayed:
            return "DELAYED"
        age = (self.received_timestamp - self.exchange_timestamp).total_seconds()
        if age < -60:
            return "CLOCK_SKEW"
        return "FRESH" if age <= 15 else "STALE"


def parse_tick(payload: dict[str, Any], source: str, received_at=None) -> MarketTick:
    if not isinstance(payload, dict):
        raise ValueError("tick must be an object")
    symbol = str(payload.get("symbol", "")).strip().upper()
    if not symbol or len(symbol) > 40:
        raise ValueError("invalid symbol")
    try:
        price = float(payload["last_price"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("last_price must be numeric")
    if not isfinite(price) or price <= 0:
        raise ValueError("last_price must be a finite positive number")
    ts = payload.get("exchange_timestamp")
    if isinstance(ts, str):
        try:
            exchange_ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            raise ValueError("invalid exchange_timestamp")
    elif isinstance(ts, datetime):
        exchange_ts = ts
    else:
        raise ValueError("exchange_timestamp is required")
    if exchange_ts.tzinfo is None:
        raise ValueError("exchange_timestamp must include timezone")
    received = received_at or datetime.now(timezone.utc)
    if received.tzinfo is None:
        raise ValueError("received_timestamp must include timezone")
    tick = MarketTick(symbol, price, exchange_ts, received, str(source), bool(payload.get("delayed", False)))
    if tick.freshness == "CLOCK_SKEW":
        raise ValueError("exchange_timestamp is more than 60 seconds in the future")
    return tick
