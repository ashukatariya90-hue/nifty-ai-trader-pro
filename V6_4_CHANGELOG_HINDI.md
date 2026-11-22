# NIFTY AI TRADER PRO V6.4 — Historical Replay Integration

- Historical CSV analysis now exposes normalized chronological OHLC rows for replay.
- Added `POST /api/replay/historical-csv?interval_ms=250` to start a controlled replay.
- Added replay status and stop endpoints.
- Replay ticks pass through the existing validated market stream and WebSocket fan-out.
- Every replay event is labelled `HISTORICAL_CSV_REPLAY`, `DELAYED`, and read-only.
- Starting a new replay clears the previous cached NIFTY event and cancels an active replay.
- Android Momentum screen can start a replay from the imported CSV and refresh replay status.
- Angel One remains a placeholder; no broker authentication, live feed, or real orders are enabled.
- Android version: 6.4.0 / versionCode 64.
- Backend regression tests: 55 passed.
- Android APK compilation has not yet been run in this environment.
