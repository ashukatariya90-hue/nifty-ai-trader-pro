# V6.3 — Native NSE Index CSV compatibility

- Recognizes NSE Index Historical Data headers: Index Name, Date, Open, High, Low, Close.
- Accepts common NSE date strings such as `20 Nov 2026`, ISO date, and supported date variants.
- Ignores unrelated columns such as Index Name.
- Automatically normalizes newest-first input into oldest-first chronological order.
- Volume remains optional and is never fabricated; VWAP/volume-dependent factors stay unavailable without it.
- CSV research backend accepts the same NSE-native format as the Android importer.
- Tested against the supplied 56-row NIFTY 50 NSE CSV: 56 rows accepted, dates normalized 2026-09-01 through 2026-11-20.
- 52 backend tests pass.
- This does not connect a live market feed or fetch current prices. It only imports user-provided historical CSV.
- Educational research, read-only, paper-only; no trade signal or real orders.
