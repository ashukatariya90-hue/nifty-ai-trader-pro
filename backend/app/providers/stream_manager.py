"""Read-only WebSocket fan-out, latest-event cache and diagnostics."""
import asyncio
from datetime import datetime, timezone


class MarketStreamManager:
    def __init__(self):
        self.clients = set()
        self.latest = {}
        self._lock = asyncio.Lock()
        self._metrics = {
            "accepted_events": 0,
            "rejected_out_of_order_events": 0,
            "broadcast_failures": 0,
        }
        self._last_event = None

    async def connect(self, websocket):
        await websocket.accept()
        async with self._lock:
            self.clients.add(websocket)

    async def disconnect(self, websocket):
        async with self._lock:
            self.clients.discard(websocket)

    async def publish(self, tick):
        """Cache and broadcast only newer events; return False for stale ordering."""
        async with self._lock:
            previous = self.latest.get(tick.symbol)
            if previous and tick.exchange_timestamp <= previous.exchange_timestamp:
                self._metrics["rejected_out_of_order_events"] += 1
                return False
            self.latest[tick.symbol] = tick
            self._metrics["accepted_events"] += 1
            self._last_event = {
                "symbol": tick.symbol,
                "source": tick.source,
                "exchange_timestamp": tick.exchange_timestamp.isoformat(),
                "received_timestamp": tick.received_timestamp.isoformat(),
                "delayed": bool(tick.delayed),
            }
            clients = list(self.clients)
        payload = {
            "type": "market_tick", "symbol": tick.symbol,
            "last_price": tick.last_price,
            "exchange_timestamp": tick.exchange_timestamp.isoformat(),
            "received_timestamp": tick.received_timestamp.isoformat(),
            "source": tick.source, "delayed": tick.delayed,
            "freshness": tick.freshness, "read_only": True,
            "real_orders_enabled": False,
        }
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                async with self._lock:
                    self._metrics["broadcast_failures"] += 1
                    self.clients.discard(ws)
        return True

    async def clear(self, symbol=None):
        """Clear cached events before starting a distinct replay session."""
        async with self._lock:
            if symbol is None:
                self.latest.clear()
                self._last_event = None
            else:
                self.latest.pop(symbol.upper(), None)
                if self._last_event and self._last_event["symbol"] == symbol.upper():
                    remaining = list(self.latest.values())
                    if remaining:
                        tick = max(remaining, key=lambda item: item.exchange_timestamp)
                        self._last_event = {
                            "symbol": tick.symbol, "source": tick.source,
                            "exchange_timestamp": tick.exchange_timestamp.isoformat(),
                            "received_timestamp": tick.received_timestamp.isoformat(),
                            "delayed": bool(tick.delayed),
                        }
                    else:
                        self._last_event = None

    def latest_snapshot(self, symbol=None):
        now = datetime.now(timezone.utc)
        selected = ({symbol.upper(): self.latest[symbol.upper()]}
                    if symbol and symbol.upper() in self.latest else self.latest)
        events = {}
        for key, tick in selected.items():
            age = (now - tick.exchange_timestamp).total_seconds()
            freshness = "DELAYED" if tick.delayed else (
                "CLOCK_SKEW" if age < -60 else "FRESH" if age <= 15 else "STALE"
            )
            events[key] = {
                "symbol": tick.symbol,
                "last_price": tick.last_price,
                "exchange_timestamp": tick.exchange_timestamp.isoformat(),
                "received_timestamp": tick.received_timestamp.isoformat(),
                "source": tick.source,
                "freshness": freshness,
                "read_only": True,
            }
        return {"status": "AVAILABLE" if events else "OFFLINE_NO_EVENTS",
                "events": events, "read_only": True,
                "real_orders_enabled": False}

    def status(self):
        now = datetime.now(timezone.utc)
        latest_age = None
        if self._last_event:
            try:
                stamp = datetime.fromisoformat(self._last_event["exchange_timestamp"])
                latest_age = round((now - stamp).total_seconds(), 3)
            except (TypeError, ValueError):
                latest_age = None
        return {
            "connected_clients": len(self.clients),
            "symbols_cached": len(self.latest),
            "metrics": dict(self._metrics),
            "last_event": dict(self._last_event) if self._last_event else None,
            "latest_event_age_seconds": latest_age,
            "diagnostics_scope": "IN_PROCESS_READ_ONLY_STREAM",
            "real_orders_enabled": False,
        }
