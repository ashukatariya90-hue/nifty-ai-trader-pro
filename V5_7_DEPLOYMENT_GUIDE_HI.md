NIFTY AI TRADER PRO V5.7 — Backend Deployment + Android API Connectivity

What changed
- Backend Dockerfile and Render Blueprint are included.
- /api/health reports service/version/mode.
- Android Integration tab now has a real HTTPS API status check.
- Android API URL is injected at build time; it is intentionally blank until a backend is deployed.

Deployment
1. Create a Render Web Service from this repository, using the included render.yaml blueprint (or set root directory=backend, runtime=Docker).
2. Wait for deployment and verify https://YOUR-SERVICE.onrender.com/api/health returns status=ok.
3. Rebuild Android with Gradle property API_BASE_URL=https://YOUR-SERVICE.onrender.com. For GitHub Actions, add a repository variable named API_BASE_URL and pass -PAPI_BASE_URL=${{ vars.API_BASE_URL }} to the Gradle build command.
4. Install that APK and tap CHECK BACKEND CONNECTION in Integration.

Important
- This is deployment-ready configuration, not an already deployed server. No public backend URL exists yet.
- Backend reachability does not mean Angel One, live market data, or news is connected.
- Do not place broker passwords, PINs, OTPs, API secrets, or session tokens in Android source, APK, or GitHub files.
- Educational/paper-only; no broker order endpoints are enabled.
