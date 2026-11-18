# NIFTY AI TRADER PRO — Version 3.0 (Educational Analysis + Paper Mode)

## Android app
- Professional dark interface with Home, Analysis, Paper, Positions and History tabs.
- Paper positions and closed-trade history are saved locally on the device and restored after app restart.
- Paper order form validates BUY/SELL stop-loss and target direction.
- Shows estimated virtual stop-loss exposure and illustrative reward/risk from the entered assumptions.
- Analysis tab calculates EMA 9, EMA 21 and RSI 14 from user-supplied closing prices (oldest to newest).
- Missing data is shown as insufficient; the app does not fabricate prices or pretend to have AI/live signals.

## FastAPI backend
- `GET /api/health` — mode and safety status.
- `GET /api/providers/angel-one` — explicit not-connected placeholder; no authentication or order methods.
- `GET /api/market` — explicit no-feed response.
- `POST /api/analysis/indicators` — educational EMA/RSI context from supplied closing prices.
- `POST /api/backtest/ema-crossover` — simple EMA 9/21 long-or-flat historical simulation with lagged signals and configurable illustrative fees (0–100 bps).
- `GET /api/paper/ledger`, `POST /api/paper/order` — backend paper ledger (in-memory; resets when backend restarts).
- API documentation appears at `/docs` when the backend is running.

## Important limitations
- PAPER / EDUCATIONAL MODE ONLY. No broker account connection, no live market feed, no real orders, and no real-money execution are implemented.
- The Android app's Analysis tab uses prices manually pasted by the user. Use only historical/market data you are authorized to access.
- The backend backtest is a simplified research example. It applies each bar's signal only to the next bar's return to reduce look-ahead bias, but does not model slippage, taxes, liquidity, expiry effects or all market frictions.
- No accuracy, profit or loss-reduction guarantee. Historical results do not predict future outcomes.
- Android paper ledger persists locally; backend API paper ledger is in-memory and resets on restart.

## Build APK using GitHub Actions
1. Upload the contents of this ZIP to the root of your existing repository (replace old files when prompted).
2. Confirm workflow path is `.github/workflows/build-apk.yml`.
3. Open the repository's Actions tab and run **Build Android APK**.
4. Download artifact `NIFTY-AI-TRADER-PRO-debug` after the run succeeds.

The workflow builds a debug APK for testing; it is not a Play Store release build.
