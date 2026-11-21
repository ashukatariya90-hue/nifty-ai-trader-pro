"""Provider-neutral news/sentiment interface; no source is connected."""
from datetime import datetime, timezone

class NewsSentimentProvider:
    async def status(self):
        return {
            "provider": None, "connected": False, "mode": "NOT_CONFIGURED",
            "items": 0, "checked_at": datetime.now(timezone.utc).isoformat(),
            "message": "No authorized news provider is configured."
        }

    async def latest_items(self, limit: int = 20):
        return []
