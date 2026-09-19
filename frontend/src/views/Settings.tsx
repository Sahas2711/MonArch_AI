import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Field, KV, Modal } from "../components/ui"
import { changePasswordRequest, checkPassword, meRequest, type AuthUser } from "../lib/auth"
import { expiresInLabel, getSession, renewSession } from "../lib/session"
import { getChatPrefs, saveChatPrefs, type ChatPrefs } from "../lib/prefs"
import { dateTimeFmt, titleCase } from "../lib/format"

export const Settings: React.FC = () => {
  const { email, name, role, authMode, userId, theme, toggleTheme, toast, signOut, go } = useApp()
  const [me, setMe] = useState<AuthUser | null>(null)
  const [prefs, setPrefs] = useState<ChatPrefs>(getChatPrefs())
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const [busy, setBusy] = useState(false)
  const [pwOpen, setPwOpen] = useState(false)

  const session = getSession()
  const strength = useMemo(() => checkPassword(next), [next])

  useEffect(() => {
    if (session?.token && session.mode === "password") {
      meRequest(session.token).then(setMe).catch(() => setMe(null))
    }
  }, [session?.token])

  const update = (patch: Partial<ChatPrefs>) => {
    const merged = { ...prefs, ...patch }
    setPrefs(merged)
    saveChatPrefs(merged)
  }

  const changePassword = async () => {
    if (!session?.token) return
    if (!strength.ok) {
      toast("New password needs: " + strength.failed.join(", ").toLowerCase(), "error")
      return
    }
    if (next !== confirm) {
      toast("The two new passwords do not match", "error")
      return
    }
    setBusy(true)
    try {
      const res = await changePasswordRequest(current, next, session.token)
      toast(res.message || "Password updated", "success")
      setPwOpen(false)
      setCurrent("")
      setNext("")
      setConfirm("")
    } catch (err: any) {
      toast(err?.message || "Could not change the password", "error")
    }
    setBusy(false)
  }

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Account</p>
            <h1>Settings</h1>
            <p>Your profile, session security and the defaults the copilot uses for every answer.</p>
          </div>
          <div className="spacer" />
          <Badge tone={authMode === "password" ? "green" : authMode === "cognito" ? "blue" : "orange"} dot>
            {authMode === "password" ? "Password session" : authMode === "cognito" ? "Cognito session" : "Local identity"}
          </Badge>
        </div>
      </div>

      <div className="grid g3">
        <div className="stack g2">
          <Card>
            <CardHead title="Profile" sub="From the account record on the API" />
            <div className="stack-sm">
              <KV k="Name" v={me?.full_name || name || "Not set"} />
              <KV k="Email" v={me?.email || email} />
              <KV k="Company" v={me?.company || "Not set"} />
              <KV k="Role" v={titleCase(me?.role || role)} />
              <KV k="User id" v={<span className="mono">{me?.user_id || userId}</span>} />
              <KV k="Member since" v={me?.created_at ? dateTimeFmt(me.created_at) : "\u2014"} />
              <KV k="Last sign-in" v={me?.last_login_at ? dateTimeFmt(me.last_login_at) : "This session"} />
            </div>
          </Card>

          <Card>
            <CardHead title="Copilot defaults" sub="Applied to every new conversation" />
            <div className="stack">
              <Field label="Answer style" hint="how the copilot writes back">
                <div className="seg">
                  {(["concise", "balanced", "thorough"] as const).map((v) => (
                    <button key={v} className={prefs.verbosity === v ? "on" : ""} onClick={() => update({ verbosity: v })}>
                      {titleCase(v)}
                    </button>
                  ))}
                </div>
              </Field>

              <Field label="Persona" hint="the voice it writes in">
                <select className="select" value={prefs.persona} onChange={(e) => update({ persona: e.target.value as ChatPrefs["persona"] })}>
                  <option value="advisor">Compliance advisor</option>
                  <option value="negotiator">Hard negotiator</option>
                  <option value="counsel">Cautious counsel</option>
                  <option value="plain">Plain English explainer</option>
                </select>
              </Field>

              <Field label={`Creativity ${prefs.temperature.toFixed(1)}`} hint="lower stays closer to the statute">
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={prefs.temperature}
                  onChange={(e) => update({ temperature: Number(e.target.value) })}
                />
              </Field>

              <div className="stack-sm">
                {([
                  ["stream", "Stream answers token by token"],
                  ["citations", "Show the retrieved passages beside each answer"],
                  ["useMemories", "Use my saved memories for context"],
                  ["evaluate", "Score answer quality with the evaluation harness"],
                  ["autoTitle", "Name conversations automatically"],
                ] as Array<[keyof ChatPrefs, string]>).map(([key, label]) => (
                  <label className="switch-row" key={key as string}>
                    <input
                      type="checkbox"
                      checked={Boolean(prefs[key])}
                      onChange={(e) => update({ [key]: e.target.checked } as Partial<ChatPrefs>)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>

              <Field label="Standing instruction" hint="prepended to every conversation">
                <textarea
                  className="textarea"
                  rows={3}
                  value={prefs.systemPrompt}
                  onChange={(e) => update({ systemPrompt: e.target.value })}
                  placeholder="We are a micro enterprise in Coimbatore. Always quote the statute section."
                />
              </Field>

              <div className="row" style={{ gap: 8 }}>
                <Button size="sm" onClick={() => go("copilot")}>Open copilot</Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    const fresh = getChatPrefs(true)
                    setPrefs(fresh)
                    saveChatPrefs(fresh)
                    toast("Copilot defaults reset", "success")
                  }}
                >
                  Reset to defaults
                </Button>
              </div>
            </div>
          </Card>
        </div>

        <div className="stack sticky-side">
          <Card>
            <CardHead title="Session" sub="Signed tokens, enforced expiry" />
            <div className="stack-sm">
              <KV k="Method" v={titleCase(authMode)} />
              <KV k="Status" v={expiresInLabel(session)} />
              <KV k="Issued" v={session ? dateTimeFmt(new Date(session.issuedAt).toISOString()) : "\u2014"} />
            </div>
            <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}>
              {authMode === "password" && (
                <Button
                  size="sm"
                  onClick={async () => toast((await renewSession()) ? "Session renewed" : "Could not renew, sign in again", "success")}
                >
                  Renew now
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={signOut}>Sign out</Button>
            </div>
          </Card>

          <Card>
            <CardHead title="Password" sub="PBKDF2, 240k rounds, per-user salt" />
            {authMode === "password" ? (
              <>
                <p className="card-sub">Changing your password signs every other device out immediately.</p>
                <Button size="sm" style={{ marginTop: 10 }} onClick={() => setPwOpen(true)}>Change password</Button>
              </>
            ) : (
              <p className="card-sub">This session came from an identity provider, so the password lives there.</p>
            )}
          </Card>

          <Card soft>
            <CardHead title="Appearance" sub="Stored on this device" />
            <div className="row" style={{ gap: 8 }}>
              <Button size="sm" onClick={toggleTheme}>{theme === "dark" ? "Switch to light" : "Switch to dark"}</Button>
            </div>
          </Card>
        </div>
      </div>

      <Modal
        open={pwOpen}
        title="Change password"
        onClose={() => setPwOpen(false)}
        footer={
          <>
            <Button onClick={() => setPwOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={busy} onClick={changePassword}>Update password</Button>
          </>
        }
      >
        <div className="stack">
          <Field label="Current password">
            <input className="input" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          </Field>
          <Field label="New password" hint={next ? strength.label : "10+ characters, mixed case, number, symbol"}>
            <input className="input" type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
          </Field>
          <div className={`pw-meter s${strength.score}`}><span /><span /><span /><span /></div>
          <Field label="Confirm new password" hint={confirm && confirm !== next ? "Does not match" : " "}>
            <input className="input" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          </Field>
        </div>
      </Modal>
    </>
  )
}
