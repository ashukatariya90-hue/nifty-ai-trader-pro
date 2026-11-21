"""Angel One read-only integration boundary; intentionally not authenticated."""
from datetime import datetime, timezone

class AngelOneMarketDataAdapter:
    provider = "Angel One SmartAPI"

    async def connect(self):
        raise RuntimeError("Placeholder only: no provider authentication or live feed is configured.")

    async def disconnect(self):
        return None

    async def status(self):
        return {
            "provider": self.provider, "connected": False, "configured": False,
            "mode": "OFFLINE_NOT_CONFIGURED", "read_only": True,
            "real_orders_enabled": False, "last_event_at": None,
            "message": "No authenticated or licensed feed is connected.",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }

    async def latest_quote(self, symbol: str):
        return None
