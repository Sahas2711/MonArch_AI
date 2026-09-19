# Fix checklist (round 5)

Everything below was reported as wrong and is now done in this build.

## Authentication

- [x] **Email-only login removed.** The sign-in form now requires a password and the backend verifies it. Typing an address grants nothing.
- [x] **Real credential store.** `auth/local_auth.py` creates `auth_users` / `auth_refresh_tokens` in SQLite. Passwords are PBKDF2-HMAC-SHA256, per-user 16-byte salt, 240,000 rounds. No plaintext, no reversible storage, no new pip dependency.
- [x] **Signed sessions.** Login returns an HS256 JWT (`AUTH_SECRET`) with `sub`, `email`, `role`, `iat`, `exp`, `iss`. The API verifies signature, expiry and issuer on every request.
- [x] **Rotating refresh tokens.** 30-day refresh tokens stored only as SHA-256 hashes, rotated on each use, revoked on logout and on password change.
- [x] **Brute-force protection.** 7 failed attempts locks the account for 15 minutes. Unknown emails still do hashing work, and the error is always the same generic message, so emails cannot be enumerated.
- [x] **Password policy enforced on both sides.** 10+ chars, upper, lower, number, symbol, common-password blocklist. The form shows a live strength meter and rule list that mirror the server rules exactly.
- [x] **Self-serve signup** (`POST /api/auth/signup`), closable with `AUTH_SIGNUP_OPEN=false`.
- [x] **Password change** (`POST /api/auth/password`) signs every other device out.
- [x] **Dev identity killed by default.** The old `dev_user_123` fallback only appears when you explicitly start the app with `VITE_ALLOW_DEV_LOGIN=true`, and the API rejects it whenever `AUTH_STRICT=true`.
- [x] **Cognito still supported** as a second method, shown only when a pool is actually configured.

## Service is gated behind login

- [x] **Server side.** `auth/dependencies.py` trusts a verified first-party token, then Cognito, and in strict mode returns `401 WWW-Authenticate: Bearer` instead of inventing a user.
- [x] **Admin endpoints role-checked.** `GET /api/admin/users` now depends on `require_admin` and returns 403 for normal users.
- [x] **Boot guard.** A deep link such as `#/copilot` while signed out redirects to sign-in and remembers where you were headed.
- [x] **Navigation guard.** Every hash change is re-checked, so URL editing cannot open a protected screen.
- [x] **Render guard.** `App.tsx` refuses to mount any protected view without a session, and the admin screen without the admin role.
- [x] **Expiry guard.** If a session dies while you are inside the app you are moved to sign-in; password sessions silently renew two minutes before expiry.
- [x] **Stored-session validation.** On load the app calls `GET /api/auth/me`; a revoked or tampered token signs you out instead of showing a fake logged-in shell.
- [x] **Calculator and pricing gated** with the rest of the workspace; only the marketing landing page and sign-in are public.

## AI chat rebuilt

- [x] Three-pane workspace: conversation rail, thread, inspector.
- [x] Saved conversations with search, pin, rename-by-first-message, delete, and clear-all.
- [x] Settings modal (also at Account → Settings): persona, answer length, creativity slider, streaming on/off, source-citing on/off, memory use, quality scoring, auto-titling, and a standing instruction prepended to every question.
- [x] Token-by-token streaming with a live caret, stop, and regenerate.
- [x] Per-message copy, useful / needs-work feedback, and the agent route that answered.
- [x] Grouped prompt packs instead of one flat suggestion row.
- [x] Sources tab shows the retrieved context; Quality tab renders the `eval_scores` meters.
- [x] Keyboard shortcuts: Enter send, Shift+Enter newline, Cmd/Ctrl+J new chat, Cmd/Ctrl+, settings, Esc stop.
- [x] Markdown transcript export and a live word count.

## Account screen (new)

- [x] Profile from `GET /api/auth/me`, session method, expiry countdown, renew now, sign out.
- [x] Change-password flow with strength meter.
- [x] Copilot defaults and theme, stored per device.

## Backend mapping verified

- [x] New rows for `/api/auth/config|signup|login|refresh|logout|me|password` in `BACKEND_MAP.md`.
- [x] `getOrg()` / `getUsage()` corrected to take no arguments.
- [x] Every other view still maps to the analyse, review, contact, negotiate, chat, ingest, documents, memories, org, billing and keys endpoints already in `api.py`.

## Required local step

Run once before judging the build, since the sandbox has no npm registry access:

```bash
cd frontend && npm install && npm run build
export AUTH_SECRET="$(openssl rand -hex 32)"
export AUTH_STRICT=true
uvicorn api:app --reload
```

Without `AUTH_SECRET` the API generates an ephemeral key and warns loudly: tokens then die on restart.
