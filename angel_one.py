class AngelOneMarketDataAdapter:
    """Read-only provider status placeholder.

    This module deliberately does not authenticate to a broker, fetch private
    account data, open a broker WebSocket, or submit orders.
    """
    async def status(self):
        return {
            "provider": "Angel One SmartAPI",
            "connected": False,
            "configured": False,
            "mode": "OFFLINE_NOT_CONFIGURED",
            "read_only": True,
            "real_orders_enabled": False,
            "message": (
                "Instrument catalogue support is available, but no authorized "
                "market-data connection is configured or verified."
            ),
        }

    async def latest_quote(self, symbol: str):
        return {
            "symbol": symbol.strip().upper(),
            "available": False,
            "source": "NOT_CONNECTED",
            "live_data_verified": False,
            "message": "No verified live quote is available.",
        }
