# NIFTY AI TRADER PRO — Version 3.0 (Educational Analysis + Paper Mode)

## Android app
- Professional dark interface with Home, Analysis, Paper, Positions and History tabs.
- Paper positions and closed-trade history are saved locally on the device and restored after app restart.
- Paper order form validates BUY/SELL stop-loss and target direction.
- Shows estimated virtual stop-loss exposure and illustrative reward/risk from the entered assumptions.
- Analysis tab calculates EMA 9, EMA 21 and RSI 14 from user-supplied closing prices (oldest to newest). RSI 14 uses Wilder smoothing (first 14 price changes seed the averages; later changes are recursively smoothed).
- Missing data is shown as insufficient; RSI requires at least 15 closing prices. The UI labels the RSI method as Wilder. The app does not fabricate prices or pretend to have AI/live signals.

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


## V5 — Advanced Educational Market Context
- EMA 9/21/50, Wilder RSI-14, MACD (12,26,9), Bollinger Bands (20, ±2 SD) and ATR-14 calculations from supplied candles.
- Recent-range support/resistance references from supplied OHLC candles; Android analysis lab also shows 20-close range references (not candle-derived levels).
- Explicit unavailable states for news sentiment, market breadth and options sentiment until authorized sources are configured.
- No fabricated live status, no BUY/SELL instructions, no broker order routing.
- Backend endpoint: `POST /api/analysis/market-context` with arrays `high`, `low`, `close`, and optional `volume`.
- This package is source code; live feed credentials and remote provider verification are not included.

## V5.1 — Integration readiness
- Provider-neutral read-only data contract and explicit Angel One placeholder retained.
- Android INTERNET permission added; cleartext HTTP disabled in the manifest.
- Provider prerequisites and validation checklist: `ANGEL_ONE_INTEGRATION_READINESS_HI.md`.
- Safe backend environment template: `backend/.env.example` (contains no secrets).
- This remains OFFLINE_NOT_CONFIGURED. It is not connected to Angel One and has no broker login/order execution.


## V5.2 — Analysis input quality update
- Analysis input accepts comma, whitespace and newline-separated historical close prices.
- Invalid/non-positive tokens are counted and reported rather than silently disappearing.
- Clear-input control and explicit 50-observation requirement for EMA 50.
- EMA now uses an initial simple-average seed before recursive smoothing.
- VWAP is explicitly marked unavailable in the Android close-only screen; backend can calculate VWAP only when matching OHLCV volume data is supplied.
- Backend market-context response identifies caller-supplied historical OHLCV basis and does not create live data or trade instructions.
- App version: 5.3.0 (versionCode 9).


## V5.3 — Historical CSV Import
- Analysis tab se phone file picker ke through historical OHLCV CSV import.
- Required columns: Date,Open,High,Low,Close,Volume (Close mandatory).
- CSV Close values se EMA/RSI/MACD/Bollinger/range context calculate hota hai.
- Complete valid High/Low/Close/Volume rows hon to typical-price VWAP calculate hota hai.
- CSV local device par read hoti hai; ye live feed nahi hai.
- Sample file: HISTORICAL_OHLCV_CSV_TEMPLATE.csv.


## V5.5 Integration Foundation
- Read-only provider contract, timestamp/freshness validation and WebSocket fan-out.
- Angel One and news adapters remain unconfigured placeholders.
- No credentials, account authentication, live feed or order execution are included.


## V6.0 Phase 3
Android dashboard ab backend ke multi-factor analysis, historical dataset validation aur walk-forward research endpoints ko call karta hai. Synthetic sample sirf integration testing ke liye hai. App educational/paper-only hai; real orders disabled hain.

## V6.1 Historical CSV Research Upgrade
- Analysis tab me imported historical CSV ab Momentum tab ke `IMPORTED HISTORICAL CSV RESEARCH` panel se backend ko bheja ja sakta hai.
- Backend OHLCV structure validation, multi-factor descriptive context aur chronological walk-forward baseline ek hi request me deta hai.
- Kam se kam 50 valid rows, required Date/Open/High/Low/Close/Volume columns aur strictly increasing timestamps zaroori hain.
- Date-only daily candles ko sirf ordering ke liye UTC midnight par normalize kiya jata hai; intraday time infer nahi hota. Time ke saath timestamp me timezone offset zaroori hai.
- Dataset structure valid hone ka matlab exchange authenticity ya licence verified hona nahi hai. Missing candles fabricate nahi hote.
- V6.1 paper-only/read-only hai; koi BUY/SELL instruction ya real order execution nahi.


## V6.2 OHLC CSV समर्थन
अब ऐतिहासिक CSV में Volume वैकल्पिक है। Date,Open,High,Low,Close के कम-से-कम 50 सही रिकॉर्ड स्वीकार होंगे। Volume न होने पर VWAP/volume factor उपलब्ध नहीं दिखेंगे; कोई volume डेटा बनाया नहीं जाएगा। ऐप research-only और paper-only रहेगा।


## V6.3 मूल NSE CSV समर्थन
अब NSE Index Historical Data की मूल CSV (Index Name, Date, Open, High, Low, Close) सीधे स्वीकार होती है। `20 Nov 2026` जैसे दिनांक पहचाने जाते हैं और नवीनतम-से-पुराने क्रम को ऐप अपने-आप पुराने-से-नए क्रम में व्यवस्थित करता है। Volume न होने पर उसे नहीं बनाया जाता। यह historical CSV import है, live market feed नहीं।
