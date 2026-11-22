# NIFTY AI TRADER PRO V5.21 — Momentum results readability

- Converts synthetic historical-analysis output into readable indicator cards for observations, EMA 9/21/50, RSI 14, MACD, MACD signal/histogram, VWAP, and ATR.
- Shows recent-range support/resistance references separately when the backend returns them.
- Keeps the raw response out of the primary summary; displays a compact success summary and clearly labels the data as synthetic.
- Corrects literal `\\n` display in simulated and historical status strings.
- Keeps all market data synthetic or user-supplied; paper-only; no live feed claims; no real broker orders.

## Verification
- Source-level checks are included in the package.
- Android APK build must be confirmed by the repository's GitHub Actions run.
