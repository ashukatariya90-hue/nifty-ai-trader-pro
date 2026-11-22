# NIFTY AI TRADER PRO V6.7.0 — Read-only stream health

- Added `/api/v6/stream-health` with stream state, per-symbol freshness, client count, heartbeat interval, and safety flags.
- Added server heartbeat messages every 20 seconds while a WebSocket remains connected and idle.
- Added WebSocket client connection-age diagnostics.
- Added `heartbeat_messages_sent` metric.
- Updated backend integration and diagnostics version to `6.7.0`.
- Added regression tests for the new endpoint and diagnostics.
- No provider authentication, brokerage credentials, or order execution was added. Angel One remains disconnected; live data remains unverified; real orders remain disabled.
