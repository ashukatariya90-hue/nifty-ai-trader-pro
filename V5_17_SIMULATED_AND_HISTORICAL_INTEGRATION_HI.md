# V5.17 — Simulated + Historical NIFTY Data Integration

- Android Momentum screen adds buttons for a synthetic snapshot and synthetic historical sample analysis.
- `GET /api/simulation/status` describes the simulator.
- `GET /api/simulation/snapshot` creates a deterministic synthetic test value and publishes it to the read-only stream cache.
- `GET /api/simulation/historical-sample?count=80` returns deterministic synthetic OHLCV candles (30–500).
- Existing `POST /api/analysis/csv` remains the route for user-provided historical OHLCV CSV files.
- The app labels generated data as synthetic. It is not NSE data, a live quote, or a trading signal.
- Paper ledger remains virtual; real broker orders remain disabled.
