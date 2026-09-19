import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Empty, Field, Modal, SkeletonRows, Stat } from "../components/ui"
import { adminUsers, eraseUserData, getHealth } from "../lib/api"
import { num, titleCase } from "../lib/format"
import type { HealthResponse } from "../types"

type AdminUser = { user_id: string; document_count: number; memory_count: number }

export const Admin: React.FC = () => {
  const { toast, role, authMode } = useApp()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [users, setUsers] = useState<AdminUser[] | null>(null)
  const [q, setQ] = useState("")
  const [sort, setSort] = useState<"documents" | "memories" | "user">("documents")
  const [target, setTarget] = useState<AdminUser | null>(null)
  const [confirmText, setConfirmText] = useState("")
  const [busy, setBusy] = useState(false)

  const load = async () => {
    const [h, u] = await Promise.all([getHealth(), adminUsers()])
    setHealth(h)
    setUsers(u as AdminUser[])
  }

  useEffect(() => {
    load()
  }, [])

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const list = (users || []).filter((u) => (needle ? u.user_id.toLowerCase().includes(needle) : true))
    return [...list].sort((a, b) =>
      sort === "user" ? a.user_id.localeCompare(b.user_id) : sort === "memories" ? b.memory_count - a.memory_count : b.document_count - a.document_count,
    )
  }, [users, q, sort])

  const totals = useMemo(
    () => ({
      users: (users || []).length,
      docs: (users || []).reduce((s, u) => s + u.document_count, 0),
      memories: (users || []).reduce((s, u) => s + u.memory_count, 0),
    }),
    [users],
  )

  const erase = async () => {
    if (!target) return
    setBusy(true)
    await eraseUserData(target.user_id)
    setBusy(false)
    setTarget(null)
    setConfirmText("")
    toast(`All data erased for ${target.user_id}`, "success")
    load()
  }

  const services: Array<[string, boolean, string]> = [
    ["API", (health?.status || "").toLowerCase() === "healthy", health?.status || "unknown"],
    ["Model", !!health?.model, health?.model || "not reported"],
    ["LangSmith tracing", !!health?.langsmith_enabled, health?.langsmith_project || "disabled"],
    ["Vector store", (health?.rag_total_documents || 0) > 0, `${num(health?.rag_total_documents)} chunks`],
  ]

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Restricted</p>
            <h1>Admin console</h1>
            <p>Service health, tenant footprint and GDPR-style erasure. Visible only to admin role holders.</p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <Badge tone="purple" dot>{titleCase(role || "admin")} · {authMode === "cognito" ? "Cognito" : "Dev identity"}</Badge>
            <Button size="sm" onClick={load}>Refresh</Button>
          </div>
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Stat label="Tenants with data" value={num(totals.users)} sub="Users holding documents or memories" />
        <Stat label="Indexed chunks" value={num(totals.docs)} tone="orange" />
        <Stat label="Stored memories" value={num(totals.memories)} tone="purple" />
        <Stat label="Vector store" value={num(health?.rag_total_documents)} sub="Reported by /api/health" tone="green" />
      </div>

      <div className="grid g3">
        <Card className="g2">
          <CardHead title="Tenant footprint" sub="Per user document and memory counts" right={<span className="count-pill">{rows.length} shown</span>} />
          <div className="toolbar" style={{ marginBottom: 12 }}>
            <input className="input search" placeholder="Search user id" value={q} onChange={(e) => setQ(e.target.value)} />
            <div className="seg">
              <button className={sort === "documents" ? "on" : ""} onClick={() => setSort("documents")}>Documents</button>
              <button className={sort === "memories" ? "on" : ""} onClick={() => setSort("memories")}>Memories</button>
              <button className={sort === "user" ? "on" : ""} onClick={() => setSort("user")}>User</button>
            </div>
          </div>
          {users === null ? (
            <SkeletonRows rows={5} height={24} />
          ) : rows.length === 0 ? (
            <Empty title="No tenants match" hint="Clear the search to see everyone with stored data." />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>User</th><th>Documents</th><th>Memories</th><th /></tr></thead>
                <tbody>
                  {rows.map((u) => (
                    <tr key={u.user_id}>
                      <td className="mono">{u.user_id}</td>
                      <td>{num(u.document_count)}</td>
                      <td>{num(u.memory_count)}</td>
                      <td style={{ textAlign: "right" }}>
                        <Button size="sm" variant="danger" onClick={() => setTarget(u)}>Erase data</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="stack sticky-side">
          <Card>
            <CardHead title="Service health" sub="Live from /api/health" />
            <div className="stack-sm">
              {services.map(([label, ok, detail]) => (
                <div className="kv" key={label}>
                  <span>{label}</span>
                  <span><Badge tone={ok ? "green" : "orange"} dot>{detail}</Badge></span>
                </div>
              ))}
            </div>
          </Card>

          <Card soft className="danger-zone">
            <CardHead title="Erasure policy" sub="What the delete actually does" />
            <ul className="check-list">
              <li>Removes every indexed chunk and memory for that user id.</li>
              <li>Audit reports stay on the organization trail for statutory record keeping.</li>
              <li>The action is logged with your admin identity and cannot be reversed.</li>
            </ul>
          </Card>
        </div>
      </div>

      <Modal
        open={!!target}
        title="Erase all data for this user"
        onClose={() => {
          setTarget(null)
          setConfirmText("")
        }}
        footer={
          <>
            <Button onClick={() => { setTarget(null); setConfirmText("") }}>Cancel</Button>
            <Button variant="danger" loading={busy} disabled={confirmText !== target?.user_id} onClick={erase}>Erase permanently</Button>
          </>
        }
      >
        {target && (
          <div className="stack">
            <div className="callout warn">
              {num(target.document_count)} document chunks and {num(target.memory_count)} memories will be deleted for{" "}
              <span className="mono">{target.user_id}</span>.
            </div>
            <Field label="Type the user id to confirm" hint={target.user_id}>
              <input className="input mono" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder={target.user_id} />
            </Field>
          </div>
        )}
      </Modal>
    </>
  )
}
