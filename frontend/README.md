# monarchAI frontend

Interactive React + TypeScript (Vite) workspace covering every backend capability.

## Run in development

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api -> http://127.0.0.1:8000
```

Start the API separately (`uvicorn api:app --reload --port 8000`).

## Build for production

```bash
npm run build        # tsc -b && vite build -> ../static/dist
```

FastAPI then serves the app at `/`, `/app`, `/pricing` and `/workbench`.

## Screens and the endpoints they use

| Screen | Backend |
| --- | --- |
| Landing | marketing only |
| Dashboard | `/api/health`, `/api/org/me/usage`, `/api/analyses` |
| Analyse contract | `POST /api/analyse` (JSON or multipart) |
| Report | `/api/analyses/{id}`, `/review`, `/contact` |
| Audit history | `GET /api/analyses` |
| Clause negotiator | `POST /api/negotiate` |
| Interest calculator | client-side Section 16 / 43B(h) maths |
| Copilot | `POST /api/chat`, `POST /api/chat/stream` (SSE), image attachments, eval toggle |
| Knowledge base | `/api/ingest`, `/api/documents/{user_id}`, `/api/memories` |
| Organization | `/api/org/create`, `/api/org/me`, `/usage`, `/history`, `/invite` |
| Plans and billing | `POST /api/billing/checkout` (Razorpay order) |
| API keys | `GET/POST /api/keys`, `DELETE /api/keys/{id}` |
| Administration | `GET /api/admin/users`, `DELETE /api/user/{id}/data` |

## Notes

- Auth: a bearer token is attached to every request when present. Sign in from the sidebar; paste a Cognito JWT if the deployment sets `AUTH_ENABLED=true`.
- Offline resilience: if the API is unreachable, reads fall back to demo fixtures and an "Offline preview data" badge appears, so the UI is always demonstrable.
- Theming: light/dark toggle persisted in `localStorage`, fully responsive down to mobile.
- Set `VITE_API_BASE` to point the build at a remote API.
