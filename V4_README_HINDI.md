# NIFTY AI TRADER PRO V4 — Read-only Market Intelligence

## What this package includes
- Android app source carried forward from V3 (paper-trading interface).
- FastAPI backend versioned as 4.0.0.
- Provider-neutral read-only market-data interface.
- Explicit OFFLINE / stale-data semantics; no fabricated live prices.
- WebSocket status endpoint at `/ws/market`.
- Existing educational indicators, backtest and virtual paper ledger.

## Important live-data limitation
This ZIP is **not connected to a live market-data provider**. No provider was
selected or licensed, and no provider credentials or official API contract
were supplied. `AuthorizedFeedAdapter` therefore fails closed and reports
`OFFLINE_NOT_CONFIGURED`. To activate a feed, a provider-specific adapter
must be implemented against that provider's current official documentation
and licensed entitlement. Do not put API keys in source code or GitHub.
Never treat delayed/demo/synthetic prices as real-time prices.

## Safety and scope
Read-only market data and educational analysis only. No broker order API,
no real-money execution, and no claim of profitable or guaranteed signals.
The paper ledger is a simulation, not a brokerage account.

## Backend local run
```bash
cd backend
python -m venv .venv
# activate the virtual environment
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Health: `/api/health`
Provider status: `/api/providers/status`
Market status: `/api/market`
WebSocket: `/ws/market`

## Android build
Existing GitHub Actions workflow builds the Android debug APK. The backend
is a separate service and is not automatically hosted by the Android APK.


## NSE public data connector (educational mode only)
- `GET /api/nse/status` discovers the available read-only tools on NSE's
  public MCP servers.
- `POST /api/nse/query` calls only an allowlist of informational tools.
  Example body:
  ```json
  {"server":"cm_market","tool":"get_market_breadth","arguments":{}}
  ```
- NSE describes intraday CM data as near-real-time delayed by about 1–3
  minutes. It is not tick-by-tick and is not intended for real-time trading,
  investment advice, or commercial deployment.
- This is an informational/learning connector. Do not use its output to
  make trades. Provider availability, tool schemas and terms can change.


    ## NSE data connector test status
    - Backend unit/integration-boundary tests: 10 passed locally.
    - Tests mock the remote NSE MCP boundary and verify route behavior, read-only allowlisting, and informational-mode flags.
    - A live remote handshake was attempted from the build environment but DNS/network access to `mcp.nseindia.in` was unavailable. Therefore a successful live NSE connection is **not yet verified**.
    - The Android dashboard is not yet wired to display NSE MCP responses; the backend endpoints are available for the next UI integration step.
