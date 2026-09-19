import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Field, Spinner } from "../components/ui"
import { checkPassword, type AuthConfig } from "../lib/auth"
import { cognitoConfigured, devLoginAllowed, hostedUiUrl, loadAuthConfig } from "../lib/session"

type Tab = "signin" | "signup" | "sso"

const PROOF = [
  ["45 days", "statutory payment window under Section 15"],
  ["3x bank rate", "compound interest you can claim under Section 16"],
  ["43B(h)", "the deduction your buyer loses until they pay"],
]

export const SignIn: React.FC = () => {
  const { signIn, signUp, signInToken, signInDev, intended, toast, go } = useApp()
  const [tab, setTab] = useState<Tab>("signin")
  const [config, setConfig] = useState<AuthConfig | null>(null)

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [fullName, setFullName] = useState("")
  const [company, setCompany] = useState("")
  const [token, setToken] = useState("")
  const [show, setShow] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [touched, setTouched] = useState(false)

  useEffect(() => {
    loadAuthConfig().then(setConfig)
  }, [])

  const strength = useMemo(() => checkPassword(password), [password])
  const emailValid = /^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$/.test(email.trim())

  const canSignIn = emailValid && password.length > 0
  const canSignUp = emailValid && strength.ok && confirm === password

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setTouched(true)
    setError("")

    if (tab === "sso") {
      const res = signInToken(token)
      if (!res.ok) setError(res.error || "That token was rejected.")
      return
    }

    if (tab === "signin" && !canSignIn) {
      setError(emailValid ? "Enter your password." : "Enter a valid email address.")
      return
    }
    if (tab === "signup" && !canSignUp) {
      setError(
        !emailValid
          ? "Enter a valid work email."
          : !strength.ok
            ? "Password needs: " + strength.failed.join(", ").toLowerCase() + "."
            : "The two passwords do not match.",
      )
      return
    }

    setBusy(true)
    const res =
      tab === "signin"
        ? await signIn(email, password)
        : await signUp({ email, password, fullName: fullName.trim() || undefined, company: company.trim() || undefined })
    setBusy(false)

    if (!res.ok) {
      setError(res.error || "Could not authenticate.")
      return
    }
    toast(tab === "signin" ? "Signed in" : "Account created", "success")
  }

  const serverReachable = config !== null

  return (
    <div className="auth">
      <aside className="auth-aside">
        <button className="logo" onClick={() => go("landing")} style={{ color: "#fff", cursor: "pointer" }} aria-label="monarchAI home">
          <img src="/monarch-mark.png" alt="monarchAI" className="logo-mark-img" style={{ width: 38, height: 38 }} />
          <span className="logo-text" style={{ fontSize: 22 }}>
            monarch<span className="logo-ai-accent">AI</span>
          </span>
        </button>

        <div className="auth-aside-body">
          <h2>Get paid what the law already owes you.</h2>
          <p>
            Audit a buyer contract, price the delay, and walk into the conversation with the statute, the interest and
            the complaint already drafted.
          </p>

          <div className="auth-proof">
            {PROOF.map(([k, v]) => (
              <div key={k}>
                <b>{k}</b>
                <span>{v}</span>
              </div>
            ))}
          </div>
        </div>

        <p className="auth-foot-note">
          Sessions are signed server side and expire on their own. Nothing in the product opens until you are
          authenticated.
        </p>
      </aside>

      <main className="auth-main">
        <div className="auth-card">
          <div className="auth-status">
            {!serverReachable ? (
              <Badge tone="orange" dot>API unreachable — start the backend</Badge>
            ) : config?.cognito_enabled ? (
              <Badge tone="green" dot>Cognito pool connected</Badge>
            ) : (
              <Badge tone="blue" dot>Email and password auth active</Badge>
            )}
          </div>

          <h1>{tab === "signup" ? "Create your workspace" : tab === "sso" ? "Single sign-on" : "Sign in"}</h1>
          <p className="auth-sub">
            {tab === "signup"
              ? "Your password is hashed with PBKDF2 before it is stored. No plaintext, ever."
              : tab === "sso"
                ? "Use your identity provider, or paste an ID token when debugging a pool."
                : intended
                  ? "Sign in to continue to the screen you requested."
                  : "Welcome back. Enter your credentials to open the workspace."}
          </p>

          <div className="seg auth-seg">
            <button className={tab === "signin" ? "on" : ""} onClick={() => { setTab("signin"); setError("") }}>Sign in</button>
            <button className={tab === "signup" ? "on" : ""} onClick={() => { setTab("signup"); setError("") }}>Create account</button>
            <button className={tab === "sso" ? "on" : ""} onClick={() => { setTab("sso"); setError("") }}>SSO</button>
          </div>

          <form className="stack" onSubmit={submit}>
            {tab !== "sso" && (
              <>
                {tab === "signup" && (
                  <div className="grid g2">
                    <Field label="Full name" hint="optional">
                      <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Gokul C S" autoComplete="name" />
                    </Field>
                    <Field label="Company" hint="optional">
                      <input className="input" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Monarch Precision Works" autoComplete="organization" />
                    </Field>
                  </div>
                )}

                <Field
                  label="Work email"
                  hint={touched && !emailValid && email ? "That address does not look right" : "used as your sign-in id"}
                >
                  <input
                    className="input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="finance@yourcompany.in"
                    autoComplete="email"
                    autoFocus
                  />
                </Field>

                <Field label="Password" hint={tab === "signup" ? strength.label : ""}>
                  <div className="input-affix">
                    <input
                      className="input"
                      type={show ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={tab === "signup" ? "At least 10 characters" : "Your password"}
                      autoComplete={tab === "signup" ? "new-password" : "current-password"}
                    />
                    <button type="button" onClick={() => setShow(!show)}>{show ? "Hide" : "Show"}</button>
                  </div>
                </Field>

                {tab === "signup" && (
                  <>
                    <div className={`pw-meter s${strength.score}`}>
                      <span />
                      <span />
                      <span />
                      <span />
                    </div>
                    <ul className="pw-rules">
                      {[
                        ["At least 10 characters", password.length >= 10],
                        ["An uppercase letter", /[A-Z]/.test(password)],
                        ["A lowercase letter", /[a-z]/.test(password)],
                        ["A number", /\d/.test(password)],
                        ["A symbol", /[^A-Za-z0-9]/.test(password)],
                      ].map(([label, ok]) => (
                        <li key={label as string} className={ok ? "ok" : ""}>
                          {ok ? "\u2713" : "\u25cb"} {label as string}
                        </li>
                      ))}
                    </ul>

                    <Field
                      label="Confirm password"
                      hint={confirm && confirm !== password ? "Passwords do not match" : "type it once more"}
                    >
                      <input
                        className="input"
                        type={show ? "text" : "password"}
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        autoComplete="new-password"
                      />
                    </Field>
                  </>
                )}
              </>
            )}

            {tab === "sso" && (
              <>
                {cognitoConfigured ? (
                  <Button type="button" variant="primary" block onClick={() => window.location.assign(hostedUiUrl("login"))}>
                    Continue with Cognito
                  </Button>
                ) : (
                  <div className="callout warn">
                    No Cognito pool is configured in this build. Set VITE_COGNITO_DOMAIN and VITE_COGNITO_CLIENT_ID to
                    enable the hosted UI, or sign in with email and password.
                  </div>
                )}
                <Field label="ID token" hint="paste a JWT if you are testing a pool directly">
                  <textarea className="textarea mono" rows={4} value={token} onChange={(e) => setToken(e.target.value)} placeholder="eyJraWQiOi..." />
                </Field>
              </>
            )}

            {error && <div className="auth-error">{error}</div>}

            <Button variant="primary" block loading={busy} disabled={busy}>
              {busy ? <Spinner size={14} /> : tab === "signup" ? "Create account and open workspace" : tab === "sso" ? "Use this token" : "Sign in"}
            </Button>
          </form>

          <div className="auth-alt">
            {tab === "signin" ? (
              <span>
                No account yet? <button onClick={() => setTab("signup")}>Create one</button>
              </span>
            ) : (
              <span>
                Already registered? <button onClick={() => setTab("signin")}>Sign in</button>
              </span>
            )}
          </div>

          {devLoginAllowed && (
            <div className="auth-dev">
              <b>Local development identity</b>
              <p>
                This build was started with VITE_ALLOW_DEV_LOGIN=true, so an unauthenticated local identity is
                available. It is disabled in normal builds.
              </p>
              <Button
                size="sm"
                onClick={() => {
                  const res = signInDev(email)
                  if (!res.ok) setError(res.error || "")
                }}
              >
                Continue as local developer
              </Button>
            </div>
          )}

          <p className="auth-legal">
            monarchAI produces drafts for review. It is not a substitute for legal advice, and every finding shows the
            clause and statute it came from.
          </p>
        </div>
      </main>
    </div>
  )
}
