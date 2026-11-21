# NIFTY AI TRADER PRO — V5.15 Read-only stream hardening

## Is update mein
- `GET /api/market/latest` endpoint added. It returns only validated events already received by the backend; otherwise it explicitly returns `OFFLINE_NO_EVENTS`.
- `GET /api/market` now reflects a cached NIFTY event only when one exists. It never fabricates a quote.
- Per-symbol event cache rejects duplicate or out-of-order exchange timestamps.
- Exchange timestamps more than 60 seconds in the future are rejected; missing timezone information is rejected.
- Freshness is reported as `FRESH`, `STALE`, `DELAYED`, or `CLOCK_SKEW`.
- All responses continue to declare read-only mode and `real_orders_enabled: false`.

## Verification
- Backend tests: 25 passed.
- Android APK compilation and physical-device testing: not run.
- Angel One SmartAPI: still NOT_CONNECTED. No credentials, authentication, provider subscription, or live feed are configured.
- News sentiment: still NOT_CONNECTED.

## Next external prerequisites
An authorized operator must confirm the current official provider documentation, account entitlement, and permitted data usage. Provider secrets must remain server-side and must never be added to Android source, APK, GitHub, logs, screenshots, or chat. Only then can a provider-specific read-only adapter be implemented and integration-tested.

## Scope and safety
This remains an educational market-information and paper-simulation project. It does not generate investment advice or route real broker orders.
