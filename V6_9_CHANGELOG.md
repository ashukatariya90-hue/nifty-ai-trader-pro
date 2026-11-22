# V6.9.0 — Persistent Paper Ledger

- Added SQLite-backed persistence for backend paper orders, fills, positions, cash, realised P&L and client-order idempotency keys.
- Every accepted order, fill and cancellation is committed to SQLite.
- Startup restores the saved ledger and validates the configured initial balance and fee policy.
- Added restart/reload regression tests.
- Render blueprint configures `/var/data/paper_ledger.sqlite3` on a 1 GB persistent disk.
- `real_orders_enabled` remains false; all ledger records remain classified as simulated.

## Deployment requirement

For persistence across Render redeploys, the service must have a Render persistent disk mounted at `/var/data`, with `PAPER_LEDGER_DB_PATH=/var/data/paper_ledger.sqlite3`. Render persistent disks may require a paid service plan. Without a mounted persistent disk, SQLite storage on the container filesystem can be lost on redeploy. Confirm the disk is attached in Render before treating persistence as production-verified.

## Scope note

The Android Paper tab continues to use its existing local app storage. This release adds persistence to the backend paper-ledger API; it does not yet synchronize the Android local ledger with the backend ledger. The two ledgers must not be treated as one account until a later, separately tested synchronization phase.
