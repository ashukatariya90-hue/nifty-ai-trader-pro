# V6.0 Phase 1 — Multi-Factor Intelligence Foundation

## Implemented
- New `POST /api/analysis/multi-factor` endpoint.
- Transparent descriptive factors: EMA alignment, RSI momentum context, recent-vs-prior volatility context, and optional relative volume.
- Explicit factor agreement and bounded context score (-2 to +2); this is not a probability or trade signal.
- Missing news sentiment, options open interest and market breadth remain explicitly `NOT_CONNECTED`.
- Input validation requires at least 50 aligned OHLC candles and rejects invalid candle geometry or malformed volume.
- Backend version metadata updated to 6.0.0.
- Five new focused unit tests.

## Verification
- Backend test suite: 33 passed.
- Android APK build and Android UI integration are not included in this phase.
- No verified market data source is connected; caller-supplied data quality/freshness remains unverified.
- Real orders remain disabled; output is descriptive and paper-only.
