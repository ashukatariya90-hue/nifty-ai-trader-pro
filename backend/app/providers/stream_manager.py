"""Read-only WebSocket fan-out and latest-event cache for validated provider events."""
import asyncio
from datetime import datetime, timezone


class MarketStreamManager:
    def __init__(self):
        self.clients = set()
        self.latest = {}
        self._lock = asyncio.Lock()

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
                return False
            self.latest[tick.symbol] = tick
            clients = list(self.clients)
        payload = {
            "type": "market_tick", "symbol": tick.symbol,
            "last_price": tick.last_price,
            "exchange_timestamp": tick.exchange_timestamp.isoformat(),
            "received_timestamp": tick.received_timestamp.isoformat(),
            "source": tick.source, "delayed": tick.delayed,
            "freshness": tick.freshness, "read_only": True
        }
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                await self.disconnect(ws)
        return True

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
        return {"connected_clients": len(self.clients), "symbols_cached": len(self.latest)}
