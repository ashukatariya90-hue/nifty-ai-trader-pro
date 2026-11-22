# NIFTY AI TRADER PRO V5.24 — Chart selector usability fix

- Replaces the cramped 20/40/80 candle selector labels with equal-width, single-number controls.
- Adds a visible-candle count line showing the selected window against the available synthetic candle sample.
- Retains the existing `takeLast(selectedWindow)` chart-window logic, OHLC candlesticks, EMA overlays, and volume bars.
- Keeps the backend unchanged and preserves synthetic-data labels and paper-only safeguards.
- Android version: 5.24.0 (versionCode 24).

## Verification notes
- Source patch applied to the V5.23 project ZIP after confirming the exact selector block and existing chart-window slicing logic.
- ZIP integrity is checked after packaging.
- Android APK compilation and on-device selector interaction still require GitHub Actions and device verification.
