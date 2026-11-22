# NIFTY AI TRADER PRO V6.0 Phase 3 — Android integration

## Android integration
- Updated Android app metadata to version 6.0.0 / versionCode 60.
- Existing historical sample workflow now calls:
  - `/api/analysis/market-context`
  - `/api/analysis/multi-factor`
  - `/api/analysis/validate-dataset`
  - `/api/research/walk-forward`
- Added dashboard summaries for factor agreement, component availability, dataset structure/gap count, and walk-forward research metrics.
- Corrected the manual analysis endpoint to `/api/analysis/multi-factor` and its payload guidance to match the 50-candle contract.
- All sample results remain labelled synthetic and research-only.

## Build workflow
- Updated GitHub Actions workflow to require the merged V6.0 Phase 3 ZIP.
- Workflow runs backend pytest before building the Android debug APK.
- Workflow excludes its own YAML from automated commits to avoid the prior workflow-permission error.
- Artifact label: `NIFTY-AI-TRADER-PRO-V6-0-debug`.

## Safety and limitations
- Educational and paper-only. No brokerage order execution is added.
- No live or licensed market data is connected by this change.
- Synthetic sample metrics are integration-test output, not evidence of real-market accuracy.
- APK build and device verification must be confirmed by GitHub Actions and installation tests; they are not claimed as completed here.
