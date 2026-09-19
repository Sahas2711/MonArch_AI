import { API_BASE } from "./api"

/**
 * Calls the first-party auth endpoints added in auth/local_auth.py.
 *
 * Every one of these hits the server. There is no client-side shortcut that
 * can mint a session, which is the point: typing an email address alone can no
 * longer get anyone into the product.
 */

export type AuthUser = {
  user_id: string
  email: string
  full_name?: string | null
  company?: string | null
  role: string
  created_at?: string
  last_login_at?: string | null
  source?: string
  expires_at?: number
}

export type AuthSessionPayload = {
  access_token: string
  token_type: string
  expires_at: number
  expires_in: number
  refresh_token: string
  user: AuthUser
}

export type AuthConfig = {
  password_auth: boolean
  cognito_enabled: boolean
  signup_open: boolean
  access_ttl_minutes: number
  password_policy: {
    min_length: number
    require_upper: boolean
    require_lower: boolean
    require_number: boolean
    require_symbol: boolean
  }
}

export class AuthError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function post<T>(path: string, body: unknown, token?: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/api/auth/${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    })
  } catch {
    throw new AuthError("Cannot reach the API. Start the backend on port 8000 and try again.", 0)
  }

  const text = await res.text()
  let data: any = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = null
  }

  if (!res.ok) {
    const detail = data?.detail
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: any) => d.msg).join(", ")
          : `Request failed with status ${res.status}.`
    throw new AuthError(message, res.status)
  }
  return data as T
}

export const signupRequest = (payload: {
  email: string
  password: string
  full_name?: string
  company?: string
}) => post<AuthSessionPayload>("signup", payload)

export const loginRequest = (email: string, password: string) =>
  post<AuthSessionPayload>("login", { email, password })

export const refreshRequest = (refresh_token: string) =>
  post<AuthSessionPayload>("refresh", { refresh_token })

export const logoutRequest = (refresh_token: string) =>
  post<{ ok: boolean }>("logout", { refresh_token }).catch(() => ({ ok: false }))

export const changePasswordRequest = (current_password: string, new_password: string, token: string) =>
  post<{ ok: boolean; message: string }>("password", { current_password, new_password }, token)

export async function meRequest(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
  if (!res.ok) throw new AuthError("Session is no longer valid.", res.status)
  return res.json()
}

export async function authConfigRequest(): Promise<AuthConfig | null> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/config`)
    if (!res.ok) return null
    return res.json()
  } catch {
    return null
  }
}

/* ------------------------------------------------------------ policy help */

export type PasswordCheck = {
  score: 0 | 1 | 2 | 3 | 4
  label: string
  failed: string[]
  ok: boolean
}

/** Mirrors password_problems() in auth/local_auth.py so the form fails fast. */
export function checkPassword(password: string): PasswordCheck {
  const rules: Array<[string, boolean]> = [
    ["At least 10 characters", password.length >= 10],
    ["An uppercase letter", /[A-Z]/.test(password)],
    ["A lowercase letter", /[a-z]/.test(password)],
    ["A number", /\d/.test(password)],
    ["A symbol", /[^A-Za-z0-9]/.test(password)],
  ]
  const failed = rules.filter(([, ok]) => !ok).map(([label]) => label)
  const passed = rules.length - failed.length
  const score = Math.max(0, Math.min(4, passed - 1)) as 0 | 1 | 2 | 3 | 4
  const label = ["Too weak", "Weak", "Fair", "Strong", "Very strong"][score]
  return { score, label, failed, ok: failed.length === 0 }
}
