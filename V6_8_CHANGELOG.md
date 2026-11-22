# NIFTY AI TRADER PRO V6.8.0 — Paper execution lifecycle

- Added explicit paper order lifecycle: ACCEPTED, FILLED, CANCELLED.
- Added simulated fill records, position accounting, weighted average price, realized P&L and configurable paper fees.
- Added notional limit, available virtual cash checks and sell-quantity checks.
- Added client order ID idempotency to prevent duplicate paper submissions.
- Added endpoints: POST /api/paper/orders, POST /api/paper/orders/{order_id}/fill, POST /api/paper/orders/{order_id}/cancel.
- Preserved legacy POST /api/paper/order behavior for compatibility.
- Ledger is in-memory and resets when the backend process restarts; no persistence is claimed.
- All activity is labelled simulated; no broker connectivity, authentication or real order routing exists. real_orders_enabled remains false.
