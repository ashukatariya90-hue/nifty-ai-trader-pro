# NIFTY AI TRADER PRO V5.20 — Deployment and paper UI correction

- Retains the V5.19 simulated snapshot and synthetic historical sample API routes.
- Adds separate in-flight UI states for verified-event refresh, synthetic snapshot generation, and synthetic historical analysis. A request in one section no longer disables or animates the other sections.
- Adds backend tests for the simulation routes and validation.
- Aligns backend and Android version metadata to 5.20.0 (Android versionCode 19).
- Updates GitHub Actions to extract the named ZIP into the repository working tree, commit extracted source files to `main`, then build the APK. The source commit uses `[skip ci]` to avoid a recursive Actions run; Render can still detect the pushed source commit.
- Paper-only safeguards remain: no Angel One authentication, no real broker order routes, no live feed claims.

## Verification
- Backend tests: run with `python -m pytest -q` in `backend/`.
- APK build: not run in this environment; GitHub Actions must verify the Android build.
- Render deployment: not run in this environment; verify the service's deployed commit and `/docs`.
