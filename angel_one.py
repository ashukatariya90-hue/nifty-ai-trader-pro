class AngelOneMarketDataAdapter:
    """Not-configured placeholder; no SmartAPI authentication or order methods."""
    async def status(self):
        return {
            "provider": "Angel One",
            "connected": False,
            "mode": "NOT_CONFIGURED",
            "message": "Live market data is not connected. Use the provider's current official documentation and authorized access for any future data integration."
        }

    async def latest_quote(self, symbol: str):
        return {
            "symbol": symbol,
            "available": False,
            "source": "NOT_CONNECTED",
            "message": "No live quote available from this placeholder."
        }
