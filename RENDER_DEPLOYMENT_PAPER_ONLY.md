# Render deployment preparation — V5.18

This configuration deploys the FastAPI backend as an educational, paper-only service.

## What Render will create
- Docker web service named `nifty-ai-trader-pro-paper`
- Dockerfile: `backend/Dockerfile`
- Docker build context: `backend/`
- Health check: `/api/health`

## Deploy
1. Put the contents of this project folder in a GitHub repository.
2. In Render, choose **New → Blueprint** and connect that repository.
3. Render should detect `render.yaml`. Review the service name and deploy.
4. When deployment completes, copy the HTTPS service URL shown by Render.
5. Open `<your-render-service-url>/api/health`. Confirm `status` is `ok`, `mode` is `EDUCATIONAL_PAPER_ONLY`, and `real_orders_enabled` is `false`.
6. Do not enter broker credentials or enable order endpoints.

## Important limitations
- This is not an Angel One-hosted service. Render hosts our backend; it does not register the app with Angel One.
- A Render URL is not a fixed outbound IP. Do not enter it as a static IP in a broker form.
- No broker authentication, API secrets, real market feed, or real-order capability is configured.
- The current paper ledger and market stream are in-memory. They reset when the service restarts or redeploys. Do not treat them as persistent records.
- Free/temporary hosting may sleep or restart and is not suitable for dependable streaming.
- The HTTPS health endpoint verifies deployment only; it does not prove market-data connectivity.

## Paper-only verification
- `/api/health`
- `/api/simulation/status`
- `/api/simulation/snapshot`
- `/api/simulation/historical-sample?count=80`

Synthetic responses are test data, not exchange prices.
