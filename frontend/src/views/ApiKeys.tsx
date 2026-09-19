import React, { useEffect, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Empty, Field, Modal, SkeletonRows } from "../components/ui"
import { createKey, listKeys, revokeKey } from "../lib/api"
import { copyText, dateTimeFmt } from "../lib/format"
import type { ApiKey } from "../types"

const SNIPPETS = (key: string) => ({
  curl: `curl -X POST https://api.monarchai.in/api/analyse \\
  -H "Authorization: Bearer $TOKEN" \\
  -H "X-API-Key: ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"buyer_name":"Larsen Industrial","contract_value":1500000,"msme_type":"micro","message":"Payment within 120 days."}'`,
  python: `import requests

res = requests.post(
    "https://api.monarchai.in/api/analyse",
    headers={"X-API-Key": "${key}"},
    json={
        "buyer_name": "Larsen Industrial",
        "contract_value": 1500000,
        "msme_type": "micro",
        "message": "Payment within 120 days.",
    },
)
report = res.json()
print(report["compliance_score"], report["risk_level"])`,
  node: `const res = await fetch("https://api.monarchai.in/api/analyse", {
  method: "POST",
  headers: { "X-API-Key": "${key}", "Content-Type": "application/json" },
  body: JSON.stringify({
    buyer_name: "Larsen Industrial",
    contract_value: 1500000,
    msme_type: "micro",
    message: "Payment within 120 days.",
  }),
})
const report = await res.json()`,
})

export const ApiKeys: React.FC = () => {
  const { toast, go } = useApp()
  const [keys, setKeys] = useState<ApiKey[] | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [name, setName] = useState("")
  const [busy, setBusy] = useState(false)
  const [fresh, setFresh] = useState<{ key: string; name: string; note?: string } | null>(null)
  const [revoking, setRevoking] = useState<ApiKey | null>(null)
  const [lang, setLang] = useState<"curl" | "python" | "node">("curl")

  const load = async () => setKeys(await listKeys())

  useEffect(() => {
    load()
  }, [])

  const create = async () => {
    if (name.trim().length < 3) return
    setBusy(true)
    const res = await createKey(name.trim())
    setBusy(false)
    setCreateOpen(false)
    setName("")
    setFresh({ key: res.key, name: res.name, note: res.note })
    load()
  }

  const doRevoke = async () => {
    if (!revoking) return
    await revokeKey(revoking.key_id)
    toast(`${revoking.name} revoked`, "success")
    setRevoking(null)
    load()
  }

  const copy = async (text: string, label: string) => {
    toast((await copyText(text)) ? `${label} copied` : "Copy blocked by the browser", "success")
  }

  const active = (keys || []).filter((k) => !k.revoked)
  const sample = active[0]?.key_prefix ? `${active[0].key_prefix}_...` : "wmb_live_..."
  const snippets = SNIPPETS(fresh?.key || sample)

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Programmatic access</p>
            <h1>API keys</h1>
            <p>Run audits from your ERP or accounting system. Keys are shown once, scoped to your organization and revocable instantly.</p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <Badge tone={active.length ? "green" : "gray"} dot>{active.length} active</Badge>
            <Button size="sm" variant="primary" onClick={() => setCreateOpen(true)}>Create key</Button>
          </div>
        </div>
      </div>

      <div className="grid g3">
        <Card className="g2">
          <CardHead title="Your keys" sub="Only the prefix is stored, so lost keys must be replaced." right={<Button size="sm" onClick={load}>Refresh</Button>} />
          {keys === null ? (
            <SkeletonRows rows={4} height={24} />
          ) : keys.length === 0 ? (
            <Empty
              icon="\u26b7"
              title="No keys yet"
              hint="Create one to call the audit API directly from your own systems."
              action={<Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>Create your first key</Button>}
            />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr><th>Name</th><th>Prefix</th><th>Created</th><th>Last used</th><th>Status</th><th /></tr>
                </thead>
                <tbody>
                  {keys.map((k) => (
                    <tr key={k.key_id} style={{ opacity: k.revoked ? 0.55 : 1 }}>
                      <td><b>{k.name}</b></td>
                      <td className="mono">{k.key_prefix}\u2026</td>
                      <td>{dateTimeFmt(k.created_at)}</td>
                      <td>{k.last_used_at ? dateTimeFmt(k.last_used_at) : "Never"}</td>
                      <td><Badge tone={k.revoked ? "red" : "green"} dot>{k.revoked ? "Revoked" : "Active"}</Badge></td>
                      <td style={{ textAlign: "right" }}>
                        {!k.revoked && <Button size="sm" variant="danger" onClick={() => setRevoking(k)}>Revoke</Button>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="stack">
          <Card>
            <CardHead title="Call the audit endpoint" sub="Copy and run" />
            <div className="code-tabs">
              {(["curl", "python", "node"] as const).map((l) => (
                <button key={l} className={lang === l ? "on" : ""} onClick={() => setLang(l)}>{l}</button>
              ))}
            </div>
            <div className="pre" style={{ whiteSpace: "pre-wrap" }}>{snippets[lang]}</div>
            <Button size="sm" style={{ marginTop: 10 }} onClick={() => copy(snippets[lang], "Snippet")}>Copy snippet</Button>
          </Card>

          <Card soft>
            <CardHead title="Good hygiene" sub="Keep the keys boring" />
            <ul className="check-list">
              <li>One key per system, named after that system.</li>
              <li>Rotate on staff changes; revoking takes effect immediately.</li>
              <li>Keys are billed against your organization quota, so watch the usage panel.</li>
            </ul>
            <Button size="sm" variant="ghost" style={{ marginTop: 10 }} onClick={() => go("organization")}>View usage</Button>
          </Card>
        </div>
      </div>

      <Modal
        open={createOpen}
        title="Create an API key"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={busy} disabled={name.trim().length < 3} onClick={create}>Create key</Button>
          </>
        }
      >
        <Field label="Name this key" hint="where it will be used">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Tally integration" />
        </Field>
      </Modal>

      <Modal
        open={!!fresh}
        title="Copy your key now"
        onClose={() => setFresh(null)}
        footer={<Button variant="primary" onClick={() => setFresh(null)}>I have stored it</Button>}
      >
        {fresh && (
          <div className="stack">
            <div className="callout warn">{fresh.note || "This secret is shown once and cannot be retrieved again."}</div>
            <div className="reveal-key">
              <span style={{ flex: 1 }}>{fresh.key}</span>
              <Button size="sm" onClick={() => copy(fresh.key, "Key")}>Copy</Button>
            </div>
            <p className="card-sub">Stored against <b>{fresh.name}</b>. Send it as the <span className="mono">X-API-Key</span> header.</p>
          </div>
        )}
      </Modal>

      <Modal
        open={!!revoking}
        title="Revoke this key"
        onClose={() => setRevoking(null)}
        footer={
          <>
            <Button onClick={() => setRevoking(null)}>Keep it</Button>
            <Button variant="danger" onClick={doRevoke}>Revoke now</Button>
          </>
        }
      >
        <p>
          Any system using <b>{revoking?.name}</b> will start receiving 401 responses immediately. This cannot be undone.
        </p>
      </Modal>
    </>
  )
}
