import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Empty, Field, Modal, SkeletonRows, Stat } from "../components/ui"
import { createOrg, getOrg, getOrgHistory, getUsage, inviteMember } from "../lib/api"
import { dateFmt, inr, num, scoreTone, titleCase } from "../lib/format"
import type { HistoryRow, Organization as Org, OrgUsage } from "../types"

export const Organization: React.FC = () => {
  const { toast, go, email, role } = useApp()
  const [org, setOrg] = useState<Org | null>(null)
  const [usage, setUsage] = useState<OrgUsage | null>(null)
  const [history, setHistory] = useState<HistoryRow[] | null>(null)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("member")
  const [busy, setBusy] = useState(false)
  const [newOrg, setNewOrg] = useState("")
  const [q, setQ] = useState("")

  const load = async () => {
    const [o, u] = await Promise.all([getOrg(), getUsage()])
    setOrg(o)
    setUsage(u)
    if (o?.org_id) {
      const h = await getOrgHistory(o.org_id)
      setHistory(h)
    } else {
      setHistory([])
    }
  }

  useEffect(() => {
    load()
  }, [])

  const members = useMemo(() => {
    const list = org?.members || []
    const needle = q.trim().toLowerCase()
    return needle ? list.filter((m) => m.email.toLowerCase().includes(needle) || m.role.toLowerCase().includes(needle)) : list
  }, [org, q])

  const invite = async () => {
    if (!org || !/.+@.+\..+/.test(inviteEmail)) {
      toast("Enter a valid work email", "error")
      return
    }
    setBusy(true)
    await inviteMember(org.org_id, inviteEmail.trim(), inviteRole)
    setBusy(false)
    setInviteOpen(false)
    setInviteEmail("")
    toast(`Invitation sent to ${inviteEmail.trim()}`, "success")
    load()
  }

  const create = async () => {
    if (newOrg.trim().length < 3) return
    setBusy(true)
    const o = await createOrg(newOrg.trim())
    setBusy(false)
    setOrg(o)
    toast(`${o.name} created`, "success")
    load()
  }

  const quota = (used: number, limit: number) => (limit < 0 ? 12 : Math.min(100, Math.round((used / Math.max(1, limit)) * 100)))
  const tone = (p: number) => (p >= 90 ? "red" : p >= 70 ? "orange" : "green")

  const recovered = (history || []).reduce(
    (sum, r) => sum + (r.report_data?.financial_summary?.total_recoverable || 0),
    0,
  )

  if (org === null) {
    return (
      <Card>
        <CardHead title="Loading organization" />
        <SkeletonRows rows={4} height={24} />
      </Card>
    )
  }

  if (!org.org_id) {
    return (
      <Card>
        <CardHead title="Create your organization" sub="Groups quotas, members and the audit trail under one account." />
        <div className="stack" style={{ maxWidth: 420 }}>
          <Field label="Organization name">
            <input className="input" value={newOrg} onChange={(e) => setNewOrg(e.target.value)} placeholder="Monarch Precision Works" />
          </Field>
          <Button variant="primary" loading={busy} disabled={newOrg.trim().length < 3} onClick={create}>Create organization</Button>
        </div>
      </Card>
    )
  }

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Workspace</p>
            <h1>{org.name}</h1>
            <p>Signed in as {email} · {titleCase(role || "member")} · {num(org.member_count)} members on the {titleCase(org.plan)} plan</p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <Button size="sm" onClick={load}>Refresh</Button>
            <Button size="sm" variant="primary" onClick={() => setInviteOpen(true)}>Invite member</Button>
          </div>
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Stat label="Plan" value={usage?.limits.name || titleCase(org.plan)} sub={usage?.limits.price_inr ? `${inr(usage.limits.price_inr)} per month` : "No charge"} />
        <Stat label="Members" value={num(org.member_count)} sub={`${(org.members || []).filter((m) => m.status === "active").length} active`} tone="purple" />
        <Stat label="Audits this cycle" value={num(usage?.usage.analyses)} sub={usage && usage.limits.analyses > 0 ? `of ${num(usage.limits.analyses)}` : "Unlimited"} tone="orange" />
        <Stat label="Recoverable found" value={inr(recovered, true)} sub="Across org audits" tone="green" />
      </div>

      <div className="grid g3">
        <div className="stack g2">
          <Card>
            <CardHead title="Members" sub="Roles decide who can review findings and manage keys." right={<span className="count-pill">{members.length}</span>} />
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <input className="input search" placeholder="Search by email or role" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            {members.length === 0 ? (
              <Empty title="No members match" hint="Clear the search to see everyone." />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Member</th><th>Role</th><th>Status</th></tr></thead>
                  <tbody>
                    {members.map((m) => (
                      <tr key={m.email}>
                        <td>
                          <div className="row" style={{ gap: 10, alignItems: "center" }}>
                            <span className="avatar-sm">{m.email.slice(0, 2).toUpperCase()}</span>
                            <span>{m.email}</span>
                          </div>
                        </td>
                        <td><Badge tone={m.role === "admin" ? "purple" : "blue"}>{titleCase(m.role)}</Badge></td>
                        <td><Badge tone={m.status === "active" ? "green" : "orange"} dot>{titleCase(m.status)}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card>
            <CardHead
              title="Organization audit trail"
              sub="Every audit run by any member"
              right={<Button size="sm" onClick={() => go("history")}>Open history</Button>}
            />
            {history === null ? (
              <SkeletonRows rows={4} height={24} />
            ) : history.length === 0 ? (
              <Empty title="No audits yet" hint="Run the first contract audit and it will show up here." action={<Button size="sm" variant="primary" onClick={() => go("analyze")}>Analyse a contract</Button>} />
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Buyer</th><th>Score</th><th>Flags</th><th>Date</th></tr></thead>
                  <tbody>
                    {history.slice(0, 8).map((r) => (
                      <tr key={r.id}>
                        <td><b>{r.buyer_name}</b><div className="card-sub">{r.file_name}</div></td>
                        <td><Badge tone={scoreTone(r.compliance_score)}>{r.compliance_score}</Badge></td>
                        <td>{r.violations_count}</td>
                        <td>{dateFmt(r.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        <div className="stack sticky-side">
          <Card>
            <CardHead title="Quota this cycle" sub="Enforced server side" right={<Button size="sm" onClick={() => go("billing")}>Upgrade</Button>} />
            {usage ? (
              <div className="stack-sm">
                {[
                  ["Contract audits", usage.usage.analyses, usage.limits.analyses],
                  ["Indexed documents", usage.usage.documents, usage.limits.documents],
                  ["Copilot messages", usage.usage.chat_messages, usage.limits.chat_messages],
                ].map(([label, used, limit]) => {
                  const p = quota(used as number, limit as number)
                  return (
                    <div className="meter-row" key={label as string}>
                      <div className="meter-top">
                        <span>{label as string}</span>
                        <b>{num(used as number)} / {(limit as number) < 0 ? "\u221e" : num(limit as number)}</b>
                      </div>
                      <div className={`meter ${tone(p)}`}><span style={{ width: `${p}%` }} /></div>
                    </div>
                  )
                })}
                <p className="card-sub" style={{ marginTop: 6 }}>
                  API access is {usage.limits.api_access ? "enabled" : "not included"} on this plan.
                </p>
              </div>
            ) : (
              <SkeletonRows rows={3} height={20} />
            )}
          </Card>

          <Card soft>
            <CardHead title="Roles" sub="What each role can do" />
            <div className="stack-sm">
              <div className="mini"><div className="k">Admin</div><div style={{ fontSize: 13, marginTop: 4 }}>Invite members, manage billing and API keys, erase data.</div></div>
              <div className="mini"><div className="k">Reviewer</div><div style={{ fontSize: 13, marginTop: 4 }}>Approve or modify audit findings before they are acted on.</div></div>
              <div className="mini"><div className="k">Member</div><div style={{ fontSize: 13, marginTop: 4 }}>Run audits, negotiate clauses, use the copilot.</div></div>
            </div>
          </Card>
        </div>
      </div>

      <Modal
        open={inviteOpen}
        title="Invite a member"
        onClose={() => setInviteOpen(false)}
        footer={
          <>
            <Button onClick={() => setInviteOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={busy} onClick={invite}>Send invitation</Button>
          </>
        }
      >
        <div className="stack">
          <Field label="Work email">
            <input className="input" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="finance@yourcompany.in" />
          </Field>
          <Field label="Role" hint="can be changed later">
            <select className="select" value={inviteRole} onChange={(e) => setInviteRole(e.target.value)}>
              <option value="member">Member</option>
              <option value="reviewer">Reviewer</option>
              <option value="admin">Admin</option>
            </select>
          </Field>
        </div>
      </Modal>
    </>
  )
}
