# NIFTY AI TRADER PRO — SmartAPI registration preparation (V5.18)

## Important status
This file prepares the project for a future provider review. It does NOT register an Angel One app, create a valid callback, allocate a static IP, authenticate an account, or connect a live feed. The current adapter remains deliberately offline and paper-only.

## Values established by this project

| Angel One form field | Project value | Status |
|---|---|---|
| App Name | NIFTY AI TRADER PRO | Suggested application label |
| Redirect URL | Not assigned | Requires an approved, deployed HTTPS callback endpoint and provider confirmation |
| Post back URL | Not assigned | Optional; only define if the provider requires a supported endpoint |
| Primary Static IP | Not assigned | Requires a deployed backend with a verified fixed public egress IP |
| Secondary Static IP | Not assigned | Only if the hosting provider supplies a second fixed public egress IP |

## Why URLs and IPs cannot be generated from Android source

A redirect URL must point to a real HTTPS endpoint that is deployed, reachable, and configured for the provider's documented callback contract. A placeholder domain, localhost address, Android deep link, or guessed URL is not a valid substitute.

The static IP must be the actual public outbound IP of the backend environment that makes provider requests. It cannot be inferred from the Android phone, a developer's current network, or this source archive. If the hosting platform does not provide fixed egress, a supported static-egress arrangement is required before entering an IP.

## Current project architecture

- Android client communicates with the FastAPI backend.
- Backend provider status remains `OFFLINE_NOT_CONFIGURED`.
- No account login, token exchange, API credential storage, live provider stream, or broker order route is implemented.
- Simulated and historical data remain clearly labelled and separate from any real provider feed.
- Paper-only mode remains the default.

## Deployment facts needed before a legitimate configuration can be reviewed

1. A deployed backend HTTPS base domain owned or controlled by the project operator.
2. Confirmation that the hosting platform provides a stable public outbound IP, plus the provider-issued value from the hosting dashboard.
3. Confirmation from the provider of the exact current callback and optional post-back requirements for the account/application type.
4. Confirmation of market-data entitlement, allowed use, symbol permissions, and display/redistribution conditions.

Do not put API keys, passwords, PINs, OTPs, JWTs, feed tokens, or refresh tokens in this file, Android source, APK, Git repository, screenshots, or chat.

## Verification checklist

- [ ] Backend deployed on HTTPS.
- [ ] Backend health endpoint reachable.
- [ ] Hosting provider confirms fixed outbound IP, if required.
- [ ] Callback contract and exact URL confirmed against current provider documentation by an eligible account operator.
- [ ] Provider entitlement and market-data terms confirmed.
- [ ] Security review completed; secrets stored only in server-side secret storage.
- [ ] Any provider integration separately tested; no simulated value is labelled live.

Until these checks are complete, leave the Angel One registration fields that depend on deployment unset. Do not submit guessed values.
