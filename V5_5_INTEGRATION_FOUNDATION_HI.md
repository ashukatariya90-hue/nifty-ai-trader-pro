# NIFTY AI TRADER PRO V5.5 — Integration Foundation

## Included
- Read-only normalized market-event contract with symbol, price and timezone validation.
- Freshness classification from exchange and receive timestamps.
- WebSocket fan-out manager for already validated provider events.
- Angel One adapter status placeholder; no authentication or vendor connection.
- News/sentiment provider interface; no source configured.
- `GET /api/v5/integration-status`
- `GET /api/news-sentiment/status`
- `POST /api/market/validate-event`

## Not included
- No Angel One credentials, account authentication, account access or order endpoints.
- No live or delayed market data is connected.
- No claim of live connection or verified vendor compatibility.
- Educational analysis and paper-only app mode remain unchanged.

Run backend tests from `backend/` with `python -m pytest -q`.
Never place credentials in Android source, APK, repository, logs, screenshots, or chat.
