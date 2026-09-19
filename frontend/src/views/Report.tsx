import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Accordion, Badge, Button, Card, CardHead, Empty, Field, Modal, ScoreRing, Stat } from "../components/ui"
import { getAnalysis, recordContact, reviewAnalysis } from "../lib/api"
import { copyText, dateFmt, download, inr, num, pct, riskTone, titleCase } from "../lib/format"

type Tab = "overview" | "violations" | "financials" | "negotiation" | "samadhaan"

export const Report: React.FC = () => {
  const { report, setReport, params, go, toast } = useApp()
  const [tab, setTab] = useState<Tab>("overview")
  const [sev, setSev] = useState("all")
  const [loading, setLoading] = useState(false)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [action, setAction] = useState("approved")
  const [reviewer, setReviewer] = useState("")
  const [notes, setNotes] = useState("")
  const [saving, setSaving] = useState(false)

  /* deep link support: #/report?id=... loads straight from the API */
  useEffect(() => {
    const id = params.id
    if (!id || report?.report_id === id) return
    setLoading(true)
    getAnalysis(id)
      .then((r) => setReport(r))
      .finally(() => setLoading(false))
  }, [params.id])

  const violations = useMemo(() => {
    const list = report?.violations || []
    return sev === "all" ? list : list.filter((v) => (v.severity || "").toLowerCase() === sev)
  }, [report, sev])

  if (loading) {
    return (
      <Card>
        <CardHead title="Loading report" sub={params.id} />
      </Card>
    )
  }

  if (!report) {
    return (
      <Empty
        icon="\u2637"
        title="No report open"
        hint="Run an audit or pick one from the history, and it will appear here with findings, exposure and drafts."
        action={
          <div className="row" style={{ gap: 8, justifyContent: "center" }}>
            <Button variant="primary" onClick={() => go("analyze")}>Analyse a contract</Button>
            <Button onClick={() => go("history")}>Open history</Button>
          </div>
        }
      />
    )
  }

  const fin = report.financial_summary || {}
  const ladder = [...(report.recommended_actions || [])].sort((a, b) => a.escalation_order - b.escalation_order)

  const submitReview = async () => {
    setSaving(true)
    const updated = await reviewAnalysis(report.report_id, { action, reviewer_name: reviewer, notes })
    setReport(updated)
    setSaving(false)
    setReviewOpen(false)
    toast(`Report marked ${action}`, "success")
  }

  const logContact = async () => {
    const res = await recordContact(report.report_id)
    setReport({ ...report, contact_attempts: res.contact_attempts, first_contact_date: res.first_contact_date, recommended_actions: res.recommended_actions })
    toast(`Contact attempt ${res.contact_attempts} recorded`, "success")
  }

  const copy = async (label: string, text: string) => {
    toast((await copyText(text)) ? `${label} copied` : "Copy blocked by the browser", "success")
  }

  const TABS: Array<[Tab, string, number | null]> = [
    ["overview", "Overview", null],
    ["violations", "Violations", report.violations?.length || 0],
    ["financials", "Financials", null],
    ["negotiation", "Counter-clauses", report.negotiation_recommendations?.length || 0],
    ["samadhaan", "Samadhaan draft", null],
  ]

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Audit report</p>
            <h1>{report.buyer_name}</h1>
            <p>
              {report.file_name} · audited {dateFmt(report.analyzed_at)} · report{" "}
              <span className="mono">{report.report_id}</span>
            </p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
            <Button size="sm" onClick={() => download(`${report.report_id}.json`, JSON.stringify(report, null, 2), "application/json")}>Download JSON</Button>
            <Button size="sm" onClick={logContact}>Log contact</Button>
            <Button size="sm" variant="primary" onClick={() => setReviewOpen(true)}>Review</Button>
          </div>
        </div>
      </div>

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Card>
          <div className="row" style={{ gap: 14, alignItems: "center" }}>
            <ScoreRing score={report.compliance_score} size={84} label="score" />
            <div>
              <Badge tone={riskTone(report.risk_level)} dot>{titleCase(report.risk_level)} risk</Badge>
              <div className="card-sub" style={{ marginTop: 6 }}>{report.violations?.length || 0} clauses flagged</div>
            </div>
          </div>
        </Card>
        <Stat label="Interest exposure" value={inr(fin.estimated_interest_exposure, true)} sub={`${fin.statutory_interest_rate_percent ?? 19.5}% compounded monthly`} tone="orange" />
        <Stat label="Tax exposure" value={inr(fin.estimated_tax_exposure, true)} sub={fin.tax_disallowance_risk ? "43B(h) disallowance likely" : "No disallowance flagged"} tone={fin.tax_disallowance_risk ? "red" : "gray"} />
        <Stat label="Total recoverable" value={inr(fin.total_recoverable, true)} sub={`Principal ${inr(fin.principal_amount, true)}`} tone="green" />
      </div>

      <div className="tabs" role="tablist">
        {TABS.map(([id, label, count]) => (
          <button key={id} role="tab" className={`tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
            {label}
            {count !== null && count > 0 ? ` (${count})` : ""}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="grid g3">
          <Card className="g2">
            <CardHead title="What the auditor found" sub="Plain-language summary" />
            <p style={{ lineHeight: 1.7 }}>{report.overall_summary}</p>
            {report.risk_score_breakdown && report.risk_score_breakdown.length > 0 && (
              <>
                <h3 style={{ margin: "20px 0 10px", fontSize: 15 }}>How the score was built</h3>
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Deduction</th><th>Points</th><th>Why</th></tr></thead>
                    <tbody>
                      {report.risk_score_breakdown.map((b, i) => (
                        <tr key={i} style={{ opacity: b.triggered ? 1 : 0.5 }}>
                          <td>{titleCase(b.deduction_name)}</td>
                          <td><b style={{ color: b.triggered ? "var(--red)" : "var(--text-dim)" }}>{b.triggered ? `-${b.points_deducted}` : "0"}</b></td>
                          <td className="card-sub">{b.rationale}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {report.risk_score_disclaimer && <p className="card-sub" style={{ marginTop: 10 }}>{report.risk_score_disclaimer}</p>}
              </>
            )}
          </Card>

          <div className="stack">
            <Card>
              <CardHead title="Recovery ladder" sub={`${report.contact_attempts || 0} contact attempts logged`} />
              {ladder.length === 0 ? (
                <div className="card-sub">No escalation steps returned for this report.</div>
              ) : (
                <div className="tl">
                  {ladder.map((a, i) => (
                    <div key={a.action_id} className={`tl-item ${a.is_recommended ? "now" : i === 0 ? "done" : ""}`}>
                      <div className="tl-dot">{a.escalation_order}</div>
                      <div className="tl-body">
                        <div className="tl-title">{a.label} {a.is_recommended && <Badge tone="blue">recommended</Badge>}</div>
                        <div className="tl-sub">{a.reason} · {titleCase(a.effort_level)} effort</div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {report.first_contact_date && <p className="card-sub" style={{ marginTop: 12 }}>First contact {dateFmt(report.first_contact_date)}</p>}
            </Card>

            {report.review_decision && (
              <Card soft>
                <CardHead
                  title="Human review"
                  sub={`Confidence ${pct(report.review_decision.confidence_score)}`}
                  right={<Badge tone={report.review_decision.needs_human_review ? "orange" : "green"} dot>{report.review_decision.needs_human_review ? "Needs review" : "Cleared"}</Badge>}
                />
                <ul className="check-list">
                  {(report.review_decision.review_reasons || []).map((r, i) => <li key={i}>{r}</li>)}
                </ul>
                {report.review_decision.recommended_action && (
                  <p className="card-sub" style={{ marginTop: 10 }}>Suggested: {titleCase(report.review_decision.recommended_action)}</p>
                )}
              </Card>
            )}

            {report.disclaimer && <Card soft><p className="card-sub">{report.disclaimer}</p></Card>}
          </div>
        </div>
      )}

      {tab === "violations" && (
        <>
          <div className="toolbar">
            <div className="chip-row">
              {["all", "critical", "high", "medium", "low"].map((s) => (
                <button key={s} className={`chip ${sev === s ? "on" : ""}`} onClick={() => setSev(s)}>{titleCase(s)}</button>
              ))}
            </div>
            <span className="count-pill">{violations.length} shown</span>
            <div className="spacer" />
            <Button size="sm" onClick={() => copy("Counter-clauses", violations.map((v) => v.draft_counter_clause || "").filter(Boolean).join("\n\n"))}>Copy all counter-clauses</Button>
          </div>
          {violations.length === 0 ? (
            <Empty title="No clauses at this severity" hint="Switch the filter to see the rest of the findings." />
          ) : (
            <div className="stack">
              {violations.map((v, i) => (
                <Card key={i}>
                  <CardHead
                    title={titleCase(v.violation_type)}
                    sub={v.cited_law}
                    right={
                      <div className="row" style={{ gap: 6 }}>
                        {v.samadhaan_ready && <Badge tone="purple">Samadhaan ready</Badge>}
                        {v.needs_human_review && <Badge tone="orange">Review</Badge>}
                        <Badge tone={riskTone(v.severity)}>{titleCase(v.severity)}</Badge>
                      </div>
                    }
                  />
                  <div className="quote-clause">{v.clause_text}</div>
                  {v.draft_counter_clause && (
                    <div className="diff" style={{ marginTop: 14 }}>
                      <div className="diff-col bad"><div className="dh">As drafted</div><div className="db">{v.clause_text}</div></div>
                      <div className="diff-col good"><div className="dh">Compliant replacement</div><div className="db">{v.draft_counter_clause}</div></div>
                    </div>
                  )}
                  <div className="row" style={{ gap: 8, marginTop: 14, flexWrap: "wrap" }}>
                    {v.confidence !== undefined && <span className="count-pill">Confidence {pct(v.confidence)}</span>}
                    {v.financial_impact?.total_financial_exposure !== undefined && (
                      <span className="count-pill">Exposure {inr(v.financial_impact.total_financial_exposure, true)}</span>
                    )}
                    <div className="spacer" />
                    {v.draft_counter_clause && (
                      <Button size="sm" onClick={() => copy("Counter-clause", v.draft_counter_clause || "")}>Copy replacement</Button>
                    )}
                  </div>
                  {v.evidence && (
                    <div style={{ marginTop: 12 }}>
                      <Accordion header={<span style={{ fontSize: 13.5, fontWeight: 600 }}>Evidence and citation</span>}>
                        <div className="stack-sm">
                          <div className="kv"><span>Statute</span><span>{v.evidence.statute_ref || v.cited_law}</span></div>
                          <div className="kv"><span>Clause reference</span><span>{v.evidence.clause_reference || "\u2014"}</span></div>
                          <div className="kv"><span>Page</span><span>{v.evidence.page_number ?? "\u2014"}</span></div>
                          {v.evidence.matched_keywords && v.evidence.matched_keywords.length > 0 && (
                            <div className="chip-row">{v.evidence.matched_keywords.map((k) => <span className="chip" key={k}>{k}</span>)}</div>
                          )}
                          <div className="pre">{v.evidence.source_text}</div>
                        </div>
                      </Accordion>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "financials" && (
        <div className="grid g3">
          <Card className="g2">
            <CardHead title="How the exposure is calculated" sub={titleCase(fin.calculation_method) + " per Section 16"} />
            <div className="mini-grid" style={{ marginBottom: 16 }}>
              <div className="mini"><div className="k">Principal</div><div className="v">{inr(fin.principal_amount, true)}</div></div>
              <div className="mini"><div className="k">Months overdue</div><div className="v">{num(fin.months_overdue)}</div></div>
              <div className="mini"><div className="k">RBI bank rate</div><div className="v">{fin.rbi_bank_rate ?? 6.5}%</div></div>
              <div className="mini"><div className="k">Statutory rate</div><div className="v">{fin.statutory_interest_rate_percent ?? 19.5}%</div></div>
              <div className="mini"><div className="k">Monthly rest</div><div className="v">{(fin.monthly_compound_rate ?? 1.625).toString()}%</div></div>
              <div className="mini"><div className="k">Delay</div><div className="v">{num(fin.estimated_delay_days)} d</div></div>
            </div>
            <div className="stack-sm">
              <div className="meter-row">
                <div className="meter-top"><span>Interest under Section 16</span><b>{inr(fin.estimated_interest_exposure)}</b></div>
                <div className="meter orange"><span style={{ width: `${Math.min(100, ((fin.estimated_interest_exposure || 0) / Math.max(1, fin.total_financial_exposure || 1)) * 100)}%` }} /></div>
              </div>
              <div className="meter-row">
                <div className="meter-top"><span>Tax disallowance under 43B(h)</span><b>{inr(fin.estimated_tax_exposure)}</b></div>
                <div className="meter red"><span style={{ width: `${Math.min(100, ((fin.estimated_tax_exposure || 0) / Math.max(1, fin.total_financial_exposure || 1)) * 100)}%` }} /></div>
              </div>
              <div className="meter-row">
                <div className="meter-top"><span>Total recoverable</span><b>{inr(fin.total_recoverable)}</b></div>
                <div className="meter green"><span style={{ width: "100%" }} /></div>
              </div>
            </div>
            <div className="row" style={{ gap: 8, marginTop: 16 }}>
              <Button size="sm" onClick={() => go("calculator")}>Open the calculator</Button>
              <Button size="sm" variant="ghost" onClick={() => copy("Financial summary", JSON.stringify(fin, null, 2))}>Copy figures</Button>
            </div>
          </Card>
          <Card>
            <CardHead title="Breakdown detail" sub="Raw values returned by the API" />
            <div className="pre">{JSON.stringify(report.financial_breakdown || fin, null, 2)}</div>
          </Card>
        </div>
      )}

      {tab === "negotiation" && (
        <div className="stack">
          {(report.negotiation_recommendations || []).length === 0 ? (
            <Empty
              icon="\u21c4"
              title="No counter-clauses on this report"
              hint="Send any clause through the negotiator to get a compliant replacement."
              action={<Button variant="primary" onClick={() => go("negotiate")}>Open the negotiator</Button>}
            />
          ) : (
            (report.negotiation_recommendations || []).map((n, i) => (
              <Card key={i}>
                <CardHead title={titleCase(n.violation_type)} sub={n.cited_law} right={<Badge tone="blue">Confidence {pct(n.confidence)}</Badge>} />
                <div className="diff">
                  <div className="diff-col bad"><div className="dh">Their clause</div><div className="db">{n.original_clause}</div></div>
                  <div className="diff-col good"><div className="dh">Your replacement</div><div className="db">{n.compliant_replacement}</div></div>
                </div>
                <p className="card-sub" style={{ marginTop: 12 }}>{n.risk_explanation}</p>
                <Button size="sm" style={{ marginTop: 10 }} onClick={() => copy("Replacement clause", n.compliant_replacement)}>Copy replacement</Button>
              </Card>
            ))
          )}
        </div>
      )}

      {tab === "samadhaan" && (
        <Card>
          <CardHead
            title="MSME Samadhaan complaint draft"
            sub="Generated from the findings on this report. Review before filing."
            right={
              <div className="row" style={{ gap: 8 }}>
                <Button size="sm" onClick={() => copy("Complaint draft", report.draft_samadhaan_complaint || "")}>Copy</Button>
                <Button size="sm" variant="primary" onClick={() => download(`samadhaan-${report.buyer_name.replace(/\s+/g, "-").toLowerCase()}.txt`, report.draft_samadhaan_complaint || "")}>Download</Button>
              </div>
            }
          />
          {report.draft_samadhaan_complaint ? (
            <div className="pre" style={{ whiteSpace: "pre-wrap" }}>{report.draft_samadhaan_complaint}</div>
          ) : (
            <Empty title="No draft generated" hint="Drafts appear when at least one clause is Samadhaan ready." />
          )}
        </Card>
      )}

      <Modal
        open={reviewOpen}
        title="Record a review decision"
        onClose={() => setReviewOpen(false)}
        footer={
          <>
            <Button onClick={() => setReviewOpen(false)}>Cancel</Button>
            <Button variant="primary" loading={saving} onClick={submitReview}>Save decision</Button>
          </>
        }
      >
        <div className="stack">
          <Field label="Decision">
            <select className="select" value={action} onChange={(e) => setAction(e.target.value)}>
              <option value="approved">Approve the findings</option>
              <option value="rejected">Reject the findings</option>
              <option value="modified">Approve with modifications</option>
            </select>
          </Field>
          <Field label="Reviewer" hint="optional">
            <input className="input" value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Your name" />
          </Field>
          <Field label="Notes" hint="stored on the audit trail">
            <textarea className="textarea" rows={4} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
        </div>
      </Modal>
    </>
  )
}
