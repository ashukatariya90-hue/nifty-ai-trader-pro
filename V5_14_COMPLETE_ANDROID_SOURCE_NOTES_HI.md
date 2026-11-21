# NIFTY AI TRADER PRO V5.14 — Complete Android Source

## Which uploaded source was used?
The `NIFTY_AI_TRADER_PRO_V5_8_1_READY_SOURCE.zip` archive was selected as the base because it contains the fuller Android project tree and GitHub Actions APK workflow. The `V5_8_EDITABLE_BACKEND_URL` archive contains a smaller/earlier copy; its Android MainActivity and app Gradle configuration were inspected and did not provide a newer Momentum screen.

## V5.14 Android changes
- Added a `Momentum` item to bottom navigation.
- Added a Momentum screen that submits caller-provided JSON to:
  `POST /api/analysis/early-momentum`
- Displays HTTP status and raw JSON response.
- Uses the saved backend URL from the existing Integration screen preference, with `BuildConfig.API_BASE_URL` as fallback.
- App version set to `5.14.0`, versionCode `14`.
- Existing Home, Analysis, Integration, Paper, Positions and History screens retained.

## How to update GitHub
This ZIP contains the complete project folder `NIFTY_AI_TRADER_PRO_V5/`.
1. Extract the ZIP on your phone/computer.
2. In GitHub, update the repository with the CONTENTS of `NIFTY_AI_TRADER_PRO_V5/` at repository root, preserving the folder paths.
3. Do not upload the outer folder as one opaque ZIP file.
4. Do not overwrite the Render backend root `main.py`, `paper.py`, `analysis.py`, `angel_one.py` or `requirements.txt` with files from this Android source archive. The archive is an Android source tree; keep the deployed backend source as already updated separately.
5. Commit changes. Open Actions and wait for the APK workflow to finish. Download the generated APK artifact only if the workflow succeeds.

## Important
- Android Gradle compilation has NOT been run in this environment. GitHub Actions is the required build verification.
- Momentum screen is a manual JSON request/response interface. It does not fetch live NSE/Angel One candles, OI, news, market breadth or FII data.
- The endpoint classifies historical/user-supplied data for paper research. It does not provide a guaranteed trade or broker order execution.
- Keep live data verification and real broker orders disabled.
