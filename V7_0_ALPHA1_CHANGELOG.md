# NIFTY AI TRADER PRO V7.0 Alpha 1

## Scope
- Adds a paper-research setup-level endpoint: `POST /api/v7/analysis/setup-levels`.
- Returns descriptive market context, recent-range support/resistance references, hypothetical entry zone, retracement zone, stop-loss/invalidation reference, three hypothetical target levels, and exit-condition descriptions.
- Requires at least 50 aligned OHLC candles and validates candle geometry and optional volume.
- Mixed/neutral context returns `NO_SETUP` rather than forcing levels.
- All outputs are explicitly unverified historical/synthetic research context; no live data, predictive probability, broker connection, or real order execution is claimed.
- Android version metadata advanced to `7.0.0-alpha1`; this alpha adds the backend API foundation only. Android UI integration is a later milestone.

## Endpoint
`POST /api/v7/analysis/setup-levels`

JSON body:
```json
{"high":[...],"low":[...],"close":[...],"volume":[...]}
```

## Limitations
The levels are mechanical references generated from EMA alignment, RSI, ATR and recent range. They are not validated entry/exit recommendations and must not be interpreted as guaranteed signals. The endpoint does not consume timestamp or source-verification metadata; it explicitly reports freshness as unverified.
