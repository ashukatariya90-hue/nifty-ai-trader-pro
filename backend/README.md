# FastAPI backend

Install: `pip install -r requirements.txt`

Run: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

Tests: `python -m pytest -q`

Interactive API docs: `http://127.0.0.1:8000/docs`

Example indicator request:

```json
{"close_prices":[100,101,100.5,102,103,102.5,104,105,104.5,106,107,106.5,108,109,110,109,111,112,113,112,114,115,116]}
```

Example backtest request requires at least 30 prices:

```json
{"close_prices":[100,101,102,101,103,104,103,105,106,105,107,108,109,108,110,111,112,111,113,114,115,114,116,117,118,117,119,120,121,120],"fee_bps":5}
```

All endpoints are educational/research only. There are no live broker connections or order execution routes.


RSI implementation: standard 14-period Wilder smoothing, seeded by the first 14 close-to-close changes. A minimum of 15 closing prices is required.


## V6.0 multi-factor foundation (descriptive, paper-only)

`POST /api/analysis/multi-factor`

Accepts aligned `high`, `low`, `close` arrays (minimum 50 candles) and optional aligned `volume`.
Returns transparent trend/momentum/volatility/volume context, factor agreement, source-quality limitations,
and explicit unavailable states for news, options open interest, and market breadth.

This endpoint does **not** produce BUY/SELL instructions, predictive probabilities, or orders.
It does not claim live-data freshness; caller-supplied source identity and timestamps are not verified.


## V6.0 Phase 2 — historical research validation

- `POST /api/analysis/validate-dataset`: validates timezone-aware OHLCV rows, chronological order, duplicate timestamps, candle geometry, finite prices/volume and optional interval gaps.
- `POST /api/research/walk-forward`: expanding-window next-bar direction-classification diagnostics using EMA9/EMA21. Each evaluation uses data available through bar t and scores the following bar t→t+1.
- Dataset checks do **not** verify exchange authenticity, licensing, completeness or survivorship bias.
- Synthetic samples are for software testing only and must never be used to claim real-market predictive accuracy.
- Research endpoints are descriptive, educational and paper-only. No BUY/SELL instructions or real order execution are provided.
