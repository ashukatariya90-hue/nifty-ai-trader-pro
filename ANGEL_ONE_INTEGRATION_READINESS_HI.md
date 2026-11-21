# Angel One integration readiness — V5.1

## Is build mein kya taiyar hai
- Provider-neutral read-only market-data contract: `backend/app/providers/base.py`
- Angel One status placeholder: `backend/app/providers/angel_one.py`
- Provider status endpoint: `GET /api/providers/status`
- Backward-compatible status endpoint: `GET /api/providers/angel-one`
- Market WebSocket endpoint currently reports `OFFLINE_NOT_CONFIGURED`; it does not invent ticks.
- Android INTERNET permission is declared so a future HTTPS backend connection can be made.
- No broker order, account login, token exchange, or trading route exists.

## Future provider integration ke liye prerequisites
1. Provider ki current official documentation aur permitted-use terms verify hon.
2. Required market-data entitlement/subscription and instrument permissions provider se confirm hon.
3. Provider-side limits, allowed symbols, streaming limits, redistribution/display rights, and regional/account restrictions confirm hon.
4. Credentials, if ever used by an authorized adult operator, must stay in a server-side secret manager; never put them in Android source, APK, GitHub, logs, screenshots, or chat.
5. Provider adapter must implement the read-only contract and validate symbol, numeric price, exchange timestamp, receive timestamp, duplicate/out-of-order events, and stale data.
6. WebSocket lifecycle must handle heartbeat, disconnect, bounded reconnect/backoff, cancellation, and clean shutdown. Do not bypass provider rate limits.
7. The UI must show provider, connection state, last received timestamp, and delayed/stale/offline status. Only verified provider events may be labelled live.
8. Run unit, contract, integration, device screen-off, network-loss/recovery, and battery tests before any release claim.

## Current status — important
This is an integration-ready scaffold, NOT an Angel One-connected build. No live data has been authenticated or tested. `OFFLINE_NOT_CONFIGURED` is the expected status. This package intentionally does not implement account authentication, broker access, or order execution.

## Safe test plan
- Run backend tests: `python -m pytest -q` from `backend/`.
- Check `/api/providers/status` and confirm it reports offline.
- Check `/api/market` and confirm no price is labelled live.
- Check `/ws/market` and confirm it sends an offline status, not fabricated ticks.
- Build Android APK and verify app networking is HTTPS-only when a backend URL is configured.
