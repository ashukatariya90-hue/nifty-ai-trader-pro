# V6.2 — OHLC historical CSV support

- Historical CSV importer now accepts Date,Open,High,Low,Close with optional Volume.
- Existing OHLCV files remain supported.
- Minimum 50 valid daily/intraday OHLC observations remains required.
- Missing volume is never fabricated. Volume factor and VWAP are marked unavailable.
- Backend historical research reports whether volume was supplied.
- Research remains descriptive, read-only and paper-only; no live feed, trade signal or real order capability.
