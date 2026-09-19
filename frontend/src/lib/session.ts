import { auth } from "./api"
import {
  AuthError,
  authConfigRequest,
  loginRequest,
  logoutRequest,
  meRequest,
  refreshRequest,
  signupRequest,
  type AuthConfig,
  type AuthSessionPayload,
} from "./auth"

/**
 * Session handling.
 *
 * Modes, in order of preference:
 *   password - email + password verified by POST /api/auth/login, HS256 token
 *              signed by the API, rotating refresh token, hard expiry
 *   cognito  - token from the Cognito hosted UI (or pasted for debugging)
 *   dev      - explicit local-only identity, available only when the build
 *              sets VITE_ALLOW_DEV_LOGIN=true. It is off by default so nobody
 *              can get in by typing an email address.
 */

export type Role = "admin" | "user" | "read_only"

export type Session = {
  mode: "password" | "cognito" | "dev"
  token: string
  refreshToken?: string
  userId: string
  email: string
  name?: string
  company?: string
  role: Role
  groups: string[]
  expiresAt: number | null
  issuedAt: number
}

const env = (import.meta as any).env || {}

export const cognito = {
  domain: (env.VITE_COGNITO_DOMAIN || "").replace(/\/$/, ""),
  clientId: env.VITE_COGNITO_CLIENT_ID || "",
  redirectUri: env.VITE_COGNITO_REDIRECT_URI || (typeof window !== "undefined" ? window.location.origin + "/" : ""),
  scope: env.VITE_COGNITO_SCOPE || "openid email profile",
}

export const cognitoConfigured = Boolean(cognito.domain && cognito.clientId)
export const devLoginAllowed = String(env.VITE_ALLOW_DEV_LOGIN || "").toLowerCase() === "true"

const KEY = "monarch.session"
const ls = typeof localStorage !== "undefined" ? localStorage : null

/* ------------------------------------------------------------------ jwt */

export function decodeJwt(token: string): Record<string, any> | null {
  try {
    const part = token.split(".")[1]
    if (!part) return null
    const json = atob(part.replace(/-/g, "+").replace(/_/g, "/"))
    return JSON.parse(decodeURIComponent(escape(json)))
  } catch {
    return null
  }
}

function roleOf(groups: string[], claimed?: string): Role {
  if (groups.includes("admin") || claimed === "admin") return "admin"
  if (groups.includes("read_only") || claimed === "read_only") return "read_only"
  return "user"
}

export function sessionFromToken(token: string, mode: "cognito" | "password" = "cognito"): Session | null {
  const claims = decodeJwt(token)
  if (!claims) return null
  const groups: string[] = claims["cognito:groups"] || claims.groups || []
  return {
    mode,
    token,
    userId: claims.sub || claims.username || claims["cognito:username"] || "user",
    email: claims.email || claims.username || "",
    name: claims.name,
    role: roleOf(groups, claims.role),
    groups,
    expiresAt: claims.exp ? claims.exp * 1000 : null,
    issuedAt: Date.now(),
  }
}

function sessionFromPayload(payload: AuthSessionPayload): Session {
  const groups = [payload.user.role]
  return {
    mode: "password",
    token: payload.access_token,
    refreshToken: payload.refresh_token,
    userId: payload.user.user_id,
    email: payload.user.email,
    name: payload.user.full_name || undefined,
    company: payload.user.company || undefined,
    role: roleOf(groups, payload.user.role),
    groups,
    expiresAt: payload.expires_at * 1000,
    issuedAt: Date.now(),
  }
}

export const isExpired = (s: Session | null) => !!s?.expiresAt && s.expiresAt <= Date.now()

export function expiresInLabel(s: Session | null): string {
  if (!s?.expiresAt) return "no expiry"
  const mins = Math.round((s.expiresAt - Date.now()) / 60000)
  if (mins <= 0) return "expired"
  if (mins < 60) return `expires in ${mins} min`
  return `expires in ${Math.round(mins / 60)} h`
}

/* -------------------------------------------------------------- storage */

const listeners = new Set<(s: Session | null) => void>()
let current: Session | null = null

function persist(s: Session | null) {
  current = s
  if (s) {
    ls?.setItem(KEY, JSON.stringify(s))
    auth.set(s.token, s.userId)
    if (s.email) ls?.setItem("monarch.email", s.email)
  } else {
    ls?.removeItem(KEY)
    auth.clear()
  }
  listeners.forEach((fn) => fn(s))
}

export const getSession = () => current
export const getToken = () => current?.token || ""

export function onSessionChange(fn: (s: Session | null) => void) {
  listeners.add(fn)
  return () => {
    listeners.delete(fn)
  }
}

/* -------------------------------------------------------- server config */

let config: AuthConfig | null = null
export const getAuthConfig = () => config
export async function loadAuthConfig(): Promise<AuthConfig | null> {
  config = await authConfigRequest()
  return config
}

/* ------------------------------------------------------------ hosted ui */

export function hostedUiUrl(kind: "login" | "signup") {
  const params = new URLSearchParams({
    client_id: cognito.clientId,
    response_type: "token",
    scope: cognito.scope,
    redirect_uri: cognito.redirectUri,
  })
  return `${cognito.domain}/${kind}?${params.toString()}`
}

export function logoutUrl() {
  const params = new URLSearchParams({ client_id: cognito.clientId, logout_uri: cognito.redirectUri })
  return `${cognito.domain}/logout?${params.toString()}`
}

function captureRedirectToken(): string | null {
  if (typeof window === "undefined") return null
  const hash = window.location.hash || ""
  if (hash.indexOf("id_token=") === -1) return null
  const frag = new URLSearchParams(hash.replace(/^#/, "").replace(/^\/?\??/, ""))
  const token = frag.get("id_token") || frag.get("access_token")
  if (token) history.replaceState(null, "", window.location.pathname + window.location.search + "#/dashboard")
  return token
}

/* ------------------------------------------------------------- lifecycle */

let expiryTimer: number | undefined
let refreshTimer: number | undefined

function armTimers(s: Session | null) {
  if (expiryTimer) window.clearTimeout(expiryTimer)
  if (refreshTimer) window.clearTimeout(refreshTimer)
  if (!s?.expiresAt) return

  const ms = s.expiresAt - Date.now()
  if (ms <= 0) {
    signOut()
    return
  }

  /* silently renew a password session two minutes before it lapses */
  if (s.mode === "password" && s.refreshToken) {
    const lead = Math.max(5_000, ms - 120_000)
    refreshTimer = window.setTimeout(() => {
      renewSession()
    }, Math.min(lead, 2_147_000_000))
  }

  expiryTimer = window.setTimeout(() => signOut(), Math.min(ms, 2_147_000_000))
}

/** Restores a stored session, validates it against the API, handles Cognito redirects. */
export function initSession(): Session | null {
  const redirectToken = captureRedirectToken()
  if (redirectToken) {
    const s = sessionFromToken(redirectToken, "cognito")
    if (s) {
      persist(s)
      armTimers(s)
      return s
    }
  }

  const raw = ls?.getItem(KEY) || ls?.getItem("wemboo.session")
  if (!raw) return null

  try {
    const s = JSON.parse(raw) as Session

    if (s.mode === "dev" && !devLoginAllowed) {
      persist(null)
      return null
    }

    if (isExpired(s)) {
      if (s.mode === "password" && s.refreshToken) {
        /* keep the user out until the refresh actually succeeds */
        renewSession(s.refreshToken)
        persist(null)
        return null
      }
      persist(null)
      return null
    }

    persist(s)
    armTimers(s)

    /* confirm with the server that the token is still accepted */
    if (s.mode === "password") {
      meRequest(s.token).catch(() => signOut())
    }
    return s
  } catch {
    persist(null)
    return null
  }
}

/* ------------------------------------------------------------- sign in/up */

export async function signInWithPassword(
  email: string,
  password: string,
): Promise<{ ok: true; session: Session } | { ok: false; error: string; status?: number }> {
  try {
    const payload = await loginRequest(email.trim().toLowerCase(), password)
    const s = sessionFromPayload(payload)
    persist(s)
    armTimers(s)
    return { ok: true, session: s }
  } catch (err) {
    const e = err as AuthError
    return { ok: false, error: e.message, status: e.status }
  }
}

export async function signUpWithPassword(input: {
  email: string
  password: string
  fullName?: string
  company?: string
}): Promise<{ ok: true; session: Session } | { ok: false; error: string; status?: number }> {
  try {
    const payload = await signupRequest({
      email: input.email.trim().toLowerCase(),
      password: input.password,
      full_name: input.fullName,
      company: input.company,
    })
    const s = sessionFromPayload(payload)
    persist(s)
    armTimers(s)
    return { ok: true, session: s }
  } catch (err) {
    const e = err as AuthError
    return { ok: false, error: e.message, status: e.status }
  }
}

/** Exchanges the refresh token for a new access token. */
export async function renewSession(refreshToken?: string): Promise<boolean> {
  const rt = refreshToken || current?.refreshToken
  if (!rt) return false
  try {
    const payload = await refreshRequest(rt)
    const s = sessionFromPayload(payload)
    persist(s)
    armTimers(s)
    return true
  } catch {
    persist(null)
    return false
  }
}

/** Cognito / debugging path: accept a pasted JWT. */
export function signInWithToken(token: string): { ok: true; session: Session } | { ok: false; error: string } {
  const trimmed = token.trim()
  if (!trimmed) return { ok: false, error: "Paste an ID token to continue." }
  const s = sessionFromToken(trimmed, "cognito")
  if (!s) return { ok: false, error: "That does not look like a JWT. Expected three dot-separated segments." }
  if (isExpired(s)) return { ok: false, error: "This token has already expired. Fetch a fresh one." }
  persist(s)
  armTimers(s)
  return { ok: true, session: s }
}

/** Local-only identity. Blocked unless the build explicitly enables it. */
export function signInAsDeveloper(email?: string): Session | null {
  if (!devLoginAllowed) return null
  const s: Session = {
    mode: "dev",
    token: "",
    userId: "dev_user_123",
    email: email?.trim() || "dev@monarch.internal",
    role: "admin",
    groups: ["admin"],
    expiresAt: Date.now() + 8 * 3600 * 1000,
    issuedAt: Date.now(),
  }
  persist(s)
  armTimers(s)
  return s
}

export function signOut(redirectToCognito = false) {
  const wasCognito = current?.mode === "cognito"
  const rt = current?.refreshToken
  if (rt) logoutRequest(rt)
  persist(null)
  if (expiryTimer) window.clearTimeout(expiryTimer)
  if (refreshTimer) window.clearTimeout(refreshTimer)
  if (redirectToCognito && wasCognito && cognitoConfigured) window.location.assign(logoutUrl())
}
