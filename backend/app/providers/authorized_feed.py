"""Safe provider adapter boundary.

No provider is connected by default. A real implementation must be supplied
for a licensed market-data subscription and the provider's current official
documentation. Never paste credentials into source code or commit them.
"""
from __future__ import annotations
from datetime import datetime, timezone
from .base import ReadOnlyMarketDataProvider, Quote

class AuthorizedFeedAdapter(ReadOnlyMarketDataProvider):
    def __init__(self):
        self._connected = False
        self._provider_name = "UNCONFIGURED_AUTHORIZED_PROVIDER"

    async def connect(self) -> None:
        # Deliberately fail closed until a provider-specific, licensed
        # read-only connector is implemented and configured.
        self._connected = False
        raise RuntimeError(
            "No licensed provider connector configured. Live data remains OFFLINE."
        )

    async def disconnect(self) -> None:
        self._connected = False

    async def quote(self, symbol: str):
        # Never synthesize or relabel a price as live.
        return None

    def status(self) -> dict:
        return {
            "provider": self._provider_name,
            "connected": self._connected,
            "mode": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "real_orders_enabled": False,
            "message": (
                "Connect a licensed provider-specific read-only adapter. "
                "No live prices are available in this build."
            ),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
