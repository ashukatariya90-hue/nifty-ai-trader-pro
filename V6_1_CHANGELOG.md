# NIFTY AI TRADER PRO V6.1 — Historical CSV Research Integration

## Main improvement
The CSV imported from the Android Analysis tab can now be submitted to the read-only backend research pipeline from the Momentum tab.

## Backend
- Added `POST /api/research/historical-csv`.
- Enforces a 2 MB CSV limit, required Date/Open/High/Low/Close/Volume columns, finite numeric values, valid OHLC candle geometry, strictly increasing timestamps and at least 50 rows.
- Date-only daily bars (`YYYY-MM-DD`) are represented at UTC midnight for ordering only. No intraday time is inferred. Timestamps that include a time must include a timezone offset.
- Returns dataset structure validation, multi-factor descriptive context, market context and chronological walk-forward baseline metrics.
- No missing candles are fabricated. Authenticity and licensing remain unverified.
- No predictive probability, BUY/SELL instruction, broker order or real-money execution is enabled.

## Android
- Analysis CSV import now requires aligned Date/Open/High/Low/Close/Volume values, valid candle geometry and at least 50 rows; invalid rows are no longer silently skipped.
- Momentum screen now includes `IMPORTED HISTORICAL CSV RESEARCH` and sends the imported file to the V6.1 endpoint.
- Result summary distinguishes structural validation from source authenticity and explicitly says interval-gap detection was not run when no interval was supplied.
- Corrected literal `\\n` display in the synthetic research status text.
- App version: 6.1.0 / versionCode 61.

## Validation
- Backend regression suite: 49 passed in local test environment.
- Android APK compilation is not verified locally; GitHub Actions must confirm it.
- The app remains educational, read-only and paper-only.
