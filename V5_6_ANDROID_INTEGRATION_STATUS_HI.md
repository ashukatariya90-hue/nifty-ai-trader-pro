NIFTY AI TRADER PRO V5.6
========================

Android update:
- Adds a dedicated Integration tab.
- Shows Angel One adapter interface, authentication state, stream state,
  event validation, news-provider state, backend API path, and paper-only mode.
- Explicitly reports that the Android app is not connected to a deployed backend URL.
- Does not display a false LIVE/CONNECTED state.

Backend:
- Retains the V5.5 read-only integration foundation and
  GET /api/v5/integration-status.
- Retains market event validation and WebSocket fan-out interfaces.

Not included:
- No Angel One authentication or account connection.
- No real or delayed market feed.
- No broker orders.
- No live data verification.

Android version: 5.6.0 (versionCode 11)
