import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Empty, ScoreRing, SkeletonRows, Stat } from "../components/ui"
import { getHealth, getUsage, listAnalyses } from "../lib/api"
import type { HealthResponse, HistoryRow, OrgUsage } from "../types"
import { dateFmt, inr, num, riskTone, scoreTone, titleCase } from "../lib/format"

type Range = 7 | 30 | 90 | 0

export const Dashboard: React.FC = () => {
  const { go, setReport, toast } = useApp()
  const [rows, setRows] = useState<HistoryRow[] | null>(null)
  const [usage, setUsage] = useState<OrgUsage | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [range, setRange] = useState<Range>(30)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setBusy(true)
    const [a, u, h] = await Promise.all([listAnalyses(), getUsage(), getHealth()])
    setRows(a)
    setUsage(u)
    setHealth(h)
    setBusy(false)
  }

  useEffect(() => {
    load()
  }, [])

  const inRange = useMemo(() => {
    if (!rows) return []
    if (!range) return rows
    const cutoff = Date.now() - range * 86400000
    return rows.filter((r) => {
      const t = new Date(r.created_at).getTime()
      return Number.isNaN(t) ? true : t >= cutoff
    })
  }, [rows, range])

  const stats = useMemo(() => {
    const count = inRange.length
    const avg = count ? Math.round(inRange.reduce((s, r) => s + (r.compliance_score || 0), 0) / count) : 0
    const violations = inRange.reduce((s, r) => s + (r.violations_count || 0), 0)
    const exposure = inRange.reduce(
      (s, r) => s + (r.report_data?.financial_summary?.total_financial_exposure || 0),
      0,
    )
    const recoverable = inRange.reduce((s, r) => s + (r.report_data?.financial_summary?.total_recoverable || 0), 0)
    const critical = inRange.filter((r) => ((r.report_data?.risk_level || "").toLowerCase().match(/high|critical/))).length
    return { count, avg, violations, exposure, recoverable, critical }
  }, [inRange])

  const byType = useMemo(() => {
    const map = new Map<string, number>()
    inRange.forEach((r) =>
      (r.report_data?.violations || []).forEach((v) => map.set(v.violation_type, (map.get(v.violation_type) || 0) + 1)),
    )
    return [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5)
  }, [inRange])

  const worst = useMemo(
    () => [...inRange].sort((a, b) => (a.compliance_score || 0) - (b.compliance_score || 0)).slice(0, 8),
    [inRange],
  )

  const maxType = Math.max(1, ...byType.map(([, n]) => n))
  const openRow = (r: HistoryRow) => {
    setReport(r.report_data)
    go("report", { id: r.id })
  }

  const quota = usage
    ? {
        used: usage.usage.analyses,
        limit: usage.limits.analyses,
        pct: usage.limits.analyses < 0 ? 0 : Math.min(100, (usage.usage.analyses / Math.max(1, usage.limits.analyses)) * 100),
      }
    : null

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Recovery position</p>
            <h1>Dashboard</h1>
            <p>
              Every contract your organization has audited, scored against the MSMED Act and priced in rupees of
              recoverable interest.
            </p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <div className="seg" role="tablist" aria-label="Time range">
              {([7, 30, 90, 0] as Range[]).map((r) => (
                <button key={r} className={range === r ? "on" : ""} onClick={() => setRange(r)}>
                  {r === 0 ? "All" : `${r}d`}
                </button>
              ))}
            </div>
            <Button size="sm" loading={busy} onClick={load}>Refresh</Button>
            <Button size="sm" variant="primary" onClick={() => go("analyze")}>New audit</Button>
          </div>
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Stat label="Audits in range" value={num(stats.count)} sub={range ? `Last ${range} days` : "All time"} />
        <Stat label="Average compliance" value={`${stats.avg}/100`} sub={`${stats.critical} high or critical risk`} tone={scoreTone(stats.avg)} />
        <Stat label="Clauses flagged" value={num(stats.violations)} sub="Across all buyers" tone="orange" />
        <Stat label="Recoverable" value={inr(stats.recoverable, true)} sub={`Exposure ${inr(stats.exposure, true)}`} tone="green" />
      </div>

      <div className="grid g3" style={{ marginBottom: 18 }}>
        <Card className="g2">
          <CardHead
            title="Lowest scoring buyers"
            sub="Sorted by compliance score. Click a bar's row below to open the report."
            right={<Badge tone="blue">{worst.length} shown</Badge>}
          />
          {rows === null ? (
            <SkeletonRows rows={4} height={22} />
          ) : worst.length === 0 ? (
            <Empty title="No audits in this range" hint="Widen the range or run a new audit." action={<Button variant="primary" size="sm" onClick={() => go("analyze")}>Analyse a contract</Button>} />
          ) : (
            <>
              <div className="bars">
                {worst.map((r) => {
                  const s = r.compliance_score || 0
                  const tone = s >= 70 ? "good" : s >= 40 ? "warn" : "bad"
                  return (
                    <div className="col" key={r.id} title={`${r.buyer_name}: ${s}/100`}>
                      <span className="val">{s}</span>
                      <div className={`bar ${tone}`} style={{ height: `${Math.max(6, s)}%` }} />
                      <span className="cap">{r.buyer_name}</span>
                    </div>
                  )
                })}
              </div>
              <div className="table-wrap" style={{ marginTop: 16 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Buyer</th>
                      <th>Risk</th>
                      <th>Flags</th>
                      <th>Exposure</th>
                      <th>Audited</th>
                    </tr>
                  </thead>
                  <tbody>
                    {worst.slice(0, 5).map((r) => (
                      <tr key={r.id} className="clickable" onClick={() => openRow(r)}>
                        <td>
                          <b>{r.buyer_name}</b>
                          <div className="card-sub">{r.file_name}</div>
                        </td>
                        <td><Badge tone={riskTone(r.report_data?.risk_level)}>{titleCase(r.report_data?.risk_level)}</Badge></td>
                        <td>{num(r.violations_count)}</td>
                        <td>{inr(r.report_data?.financial_summary?.total_financial_exposure, true)}</td>
                        <td>{dateFmt(r.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Card>

        <div className="stack">
          <Card>
            <CardHead title="Portfolio health" sub="Average across the range" />
            <div className="row" style={{ gap: 16, alignItems: "center" }}>
              <ScoreRing score={stats.avg} label="avg" />
              <div className="stack-sm" style={{ flex: 1 }}>
                <div className="meter-row">
                  <div className="meter-top"><span>High or critical</span><b>{stats.critical}</b></div>
                  <div className="meter red"><span style={{ width: `${stats.count ? (stats.critical / stats.count) * 100 : 0}%` }} /></div>
                </div>
                <div className="meter-row">
                  <div className="meter-top"><span>Flags per audit</span><b>{stats.count ? (stats.violations / stats.count).toFixed(1) : "0"}</b></div>
                  <div className="meter orange"><span style={{ width: `${Math.min(100, (stats.violations / Math.max(1, stats.count)) * 20)}%` }} /></div>
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHead title="Most common breaches" sub="Clause types the auditor flags most" />
            {byType.length === 0 ? (
              <div className="card-sub">Nothing flagged yet.</div>
            ) : (
              <div className="stack-sm">
                {byType.map(([type, n]) => (
                  <div className="meter-row" key={type}>
                    <div className="meter-top"><span>{titleCase(type)}</span><b>{n}</b></div>
                    <div className="meter"><span style={{ width: `${(n / maxType) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card soft>
            <CardHead
              title="Plan usage"
              sub={usage ? usage.limits.name : "Loading"}
              right={usage ? <Badge tone={usage.plan === "free" ? "gray" : "green"}>{titleCase(usage.plan)}</Badge> : undefined}
            />
            {quota && (
              <div className="meter-row" style={{ marginBottom: 12 }}>
                <div className="meter-top">
                  <span>Audits this cycle</span>
                  <b>{quota.limit < 0 ? `${quota.used} / unlimited` : `${quota.used} / ${quota.limit}`}</b>
                </div>
                <div className={`meter ${quota.pct > 85 ? "red" : quota.pct > 60 ? "orange" : ""}`}>
                  <span style={{ width: `${quota.pct}%` }} />
                </div>
              </div>
            )}
            <div className="row" style={{ gap: 8 }}>
              <Button size="sm" onClick={() => go("billing")}>Plans</Button>
              <Button size="sm" variant="ghost" onClick={() => go("organization")}>Organization</Button>
            </div>
          </Card>
        </div>
      </div>

      <div className="grid g3">
        <Card>
          <CardHead title="Service health" sub="Live from /api/health" right={<Badge tone={health?.status === "ok" ? "green" : "orange"} dot>{health?.status || "unknown"}</Badge>} />
          <div className="mini-grid">
            <div className="mini"><div className="k">Model</div><div className="v" style={{ fontSize: 13 }}>{health?.model || "\u2014"}</div></div>
            <div className="mini"><div className="k">RAG chunks</div><div className="v">{num(health?.rag_total_documents)}</div></div>
            <div className="mini"><div className="k">Tracing</div><div className="v" style={{ fontSize: 13 }}>{health?.langsmith_enabled ? "On" : "Off"}</div></div>
          </div>
        </Card>

        <Card>
          <CardHead title="Next best actions" sub="Recommended by the escalation ladder" />
          <div className="tl">
            <div className="tl-item done"><div className="tl-dot">1</div><div className="tl-body"><div className="tl-title">Audit the contract</div><div className="tl-sub">{stats.count} done in this range.</div></div></div>
            <div className={`tl-item ${stats.violations ? "now" : ""}`}><div className="tl-dot">2</div><div className="tl-body"><div className="tl-title">Send a demand with interest</div><div className="tl-sub">{inr(stats.recoverable, true)} recoverable under Section 16.</div></div></div>
            <div className="tl-item"><div className="tl-dot">3</div><div className="tl-body"><div className="tl-title">File on Samadhaan</div><div className="tl-sub">Drafts are generated on every report.</div></div></div>
          </div>
        </Card>

        <Card>
          <CardHead title="Jump straight in" sub="Keyboard shortcut \u2318K opens the palette" />
          <div className="stack-sm">
            <Button block onClick={() => go("analyze")}>Analyse a contract</Button>
            <Button block onClick={() => go("negotiate")}>Rewrite a clause</Button>
            <Button block onClick={() => go("calculator")}>Interest calculator</Button>
            <Button block variant="ghost" onClick={() => { toast("Opening the audit history"); go("history") }}>All audits</Button>
          </div>
        </Card>
      </div>
    </>
  )
}
