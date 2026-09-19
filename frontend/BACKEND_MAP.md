# Backend coverage map

Every route in `api.py` and every schema in `models/schemas.py` checked against the frontend.

## Routes

| # | Method + path | api.py | Frontend caller (`src/lib/api.ts`) | Screen |
|---|---|---|---|---|
| 1 | `GET /` | 128 | server-rendered SPA shell | — |
| 2 | `GET /pricing` | 142 | SPA shell, deep link `#/pricing` | Plans and billing |
| 3 | `GET /app` | 154 | SPA shell, deep link `#/dashboard` | Dashboard |
| 4 | `GET /workbench` | 168 | SPA shell, deep link `#/analyse` | Analyse |
| 5 | `GET /api/health` | 261 | `getHealth` | Dashboard, Administration |
| 6 | `POST /api/chat` | 273 | `chat` | Copilot (non-stream fallback) |
| 7 | `POST /api/chat/stream` | 340 | `streamChat` (SSE: route / token / done / error) | Copilot |
| 8 | `POST /api/ingest` | 403 | `ingest` | Knowledge base |
| 9 | `GET /api/documents/{user_id}` | 434 | `listDocuments` | Knowledge base |
| 10 | `DELETE /api/documents/{user_id}` | 445 | `deleteDocuments` | Knowledge base |
| 11 | `GET /api/memories/{user_id}` | 457 | `listMemories` | Knowledge base |
| 12 | `POST /api/memories` | 464 | `addMemory` | Knowledge base |
| 13 | `DELETE /api/user/{user_id}/data` | 471 | `eraseUserData` | Administration |
| 14 | `GET /api/admin/users` | 485 | `adminUsers` | Administration |
| 15 | `POST /api/analyse` (JSON) | 503 | `analyseText` | Analyse |
| 16 | `POST /api/analyse` (multipart) | 503 | `analyseFile` | Analyse |
| 17 | `GET /api/analyses` | 969 | `listAnalyses` | Audit history, Dashboard |
| 18 | `GET /api/analyses/{report_id}` | 1018 | `getAnalysis` | Report (deep link `#/report?id=`) |
| 19 | `POST /api/analyses/{report_id}/review` | 1037 | `reviewAnalysis` | Report |
| 20 | `POST /api/analyses/{report_id}/contact` | 1092 | `recordContact` | Report recovery ladder |
| 21 | `POST /api/negotiate` | 1218 | `negotiate` | Clause negotiator |
| 22 | `POST /api/org/create` | 1282 | `createOrg` | Organization |
| 23 | `GET /api/org/me` | 1303 | `getOrg()` | Organization |
| 24 | `GET /api/org/{org_id}` | 1304 | `getOrg(orgId)` | Organization |
| 25 | `GET /api/org/me/usage` | 1318 | `getUsage()` | Dashboard, Billing |
| 26 | `GET /api/org/{org_id}/usage` | 1319 | `getUsage(orgId)` | Organization |
| 27 | `GET /api/org/{org_id}/history` | 1343 | `getOrgHistory` | Organization |
| 28 | `POST /api/org/{org_id}/invite` | 1380 | `inviteMember` | Organization |
| 29 | `POST /api/billing/checkout` | 1405 | `checkout` | Plans and billing |
| 30 | `POST /api/billing/webhook` | 1447 | none by design — Razorpay calls this server to server | — |
| 31 | `GET /api/keys` | 1488 | `listKeys` | API keys |
| 32 | `POST /api/keys` | 1514 | `createKey` | API keys |
| 33 | `DELETE /api/keys/{key_id}` | 1543 | `revokeKey` | API keys |

## Schemas

`AnalysisReport`, `ViolationItem`, `EvidenceItem`, `FinancialImpact`, `RiskScoreBreakdown`,
`RecommendedActionSchema`, `ReviewDecisionSchema`, `NegotiationRecommendation`, `HistoryRow`,
`OrgUsage`, `Organization`, `ApiKey`, `ChatResponse`, `HealthResponse` are all mirrored in
`src/types/index.ts` with the same field names, so the SQL-shaped payloads land in the UI
without translation.

## Authentication contract

`auth/dependencies.py` reads `Authorization: Bearer <jwt>` and hands it to
`auth/cognito.py::verify_jwt_token`. There is **no login, signup or token endpoint on the
backend** — the token is issued by an Amazon Cognito user pool. When `AUTH_ENABLED` is not
`true` (the default) any request resolves to `dev_user_123` with the `admin` role.

The frontend therefore offers exactly what the backend can honour:

| Mode | What happens | Requires |
|---|---|---|
| Email and password | Redirects to the Cognito hosted UI, which returns an `id_token` in the URL fragment; the token is captured, decoded and stored | `VITE_COGNITO_DOMAIN`, `VITE_COGNITO_CLIENT_ID`, optional `VITE_COGNITO_REDIRECT_URI` |
| ID token | Paste a token from Cognito or the CLI; decoded locally for `sub`, `email`, `cognito:groups`, then sent on every request | nothing |
| Development identity | No token is sent, matching the server fallback; the UI labels the session honestly | `AUTH_ENABLED=false` |

Session rules: stored under `wemboo.session`, expiry read from the JWT `exp` claim with an
automatic sign-out timer, `cognito:groups` drives the admin-only screens, and sign-out clears
storage and returns to the marketing site.

## Routing

Hash routing (`#/dashboard`, `#/report?id=...`, `#/signin`) because FastAPI only serves the SPA
shell on `/`, `/app`, `/pricing` and `/workbench`. Every screen is refreshable and shareable,
back and forward work, and protected routes bounce to `#/signin` and return to the intended
screen after sign-in.

## Authentication endpoints (added in this round)

| Endpoint | Method | Frontend caller | Notes |
| --- | --- | --- | --- |
| `/api/auth/config` | GET | `authConfigRequest()` via `loadAuthConfig()` | Reports whether signup is open and whether a Cognito pool is configured. Also used as the API reachability probe on the sign-in screen. |
| `/api/auth/signup` | POST | `signupRequest()` / `store.signUp()` | `{email, password, full_name?, company?}` -> 201 with access token, refresh token and user. |
| `/api/auth/login` | POST | `loginRequest()` / `store.signIn()` | `{email, password}` -> access + refresh token. Generic 401 on bad credentials, 429 while locked out. |
| `/api/auth/refresh` | POST | `refreshRequest()` via `renewSession()` | Rotates the refresh token, issues a new access token. Called automatically two minutes before expiry. |
| `/api/auth/logout` | POST | `logoutRequest()` via `signOut()` | Revokes the presented refresh token. |
| `/api/auth/me` | GET | `meRequest(token)` | Used on boot to validate a stored session and on the Settings screen for the profile block. |
| `/api/auth/password` | POST | `changePasswordRequest()` | `{current_password, new_password}`. Revokes every refresh token for the user. |

### Correction

`getOrg()` and `getUsage()` in `src/lib/api.ts` take no arguments; they call `/api/org/me` and
`/api/org/me/usage` and resolve the org from the authenticated session. Earlier rows in this file that
showed `getOrg(orgId)` / `getUsage(orgId)` were wrong.
