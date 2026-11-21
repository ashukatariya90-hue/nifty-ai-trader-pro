# V5.16 — Momentum Screen Market Snapshot Connection

- Android Momentum screen now calls `GET /api/market/latest?symbol=NIFTY`.
- Displays only the backend's cached validated event and its source, freshness, and exchange timestamp.
- Explicitly displays when no event is cached; it never invents a price.
- Existing manual completed-candle analysis remains available.
- No broker authentication or order placement was added. Paper-only behavior is unchanged.
- Requires a deployed backend that exposes `/api/market/latest`. The endpoint returns OFFLINE_NO_EVENTS until a validated provider event is published.
- APK compilation and device testing still require Android SDK/Gradle build verification.
