# NIFTY AI TRADER PRO — V5.8.1 Update Notes (Hindi)

## Android Integration tab
- Backend HTTPS URL edit field is available.
- `SAVE BACKEND URL` stores the URL locally on this Android device using SharedPreferences.
- Saved URL remains after app restart.
- Default URL: `https://nifty-ai-trader-pro.onrender.com`
- `CHECK BACKEND CONNECTION` checks `GET /api/v5/integration-status`.
- UI updates from the Android main thread after the network request completes.

## Safety
- Educational / paper-only mode.
- No real broker order execution.
- No live market feed is claimed as verified.
- No broker credentials or API secrets are required for this URL setting.

## Backend
- Health endpoint includes the virtual-capital field expected by the test suite.
- Integration status endpoint remains read-only.

## Validation performed
- Backend tests: 22 passed locally.
- Android Gradle build was not run in this environment because Gradle/Android SDK are not installed here. GitHub Actions must complete successfully before installing the new APK.
- A successful Render deploy only confirms the backend deploy; it does not build or update the Android APK.
