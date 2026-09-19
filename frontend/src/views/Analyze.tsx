import React, { useEffect, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Dropzone, Field, ScoreRing, Stat } from "../components/ui"
import { analyseFile, analyseText } from "../lib/api"
import { inr, num, riskTone, titleCase } from "../lib/format"
import type { AnalysisReport } from "../types"

const SAMPLE = `Payment shall be released within 120 days of submission of invoice, subject to internal approvals.
The Buyer may withhold or adjust any amount at its sole discretion without prior notice.
No interest shall be payable on delayed payments under any circumstances.
All disputes shall be subject to arbitration in Singapore under the laws of Singapore.`

const STEPS = [
  "Splitting the document into clauses",
  "Retrieving MSMED Act passages",
  "Matching clauses against statute",
  "Pricing interest and tax exposure",
  "Drafting counter-clauses and Samadhaan",
]

export const Analyze: React.FC = () => {
  const { go, setReport, toast } = useApp()
  const [mode, setMode] = useState<"paste" | "upload">("paste")
  const [text, setText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [buyer, setBuyer] = useState("")
  const [value, setValue] = useState("")
  const [msme, setMsme] = useState("micro")
  const [busy, setBusy] = useState(false)
  const [step, setStep] = useState(0)
  const [result, setResult] = useState<AnalysisReport | null>(null)
  const [err, setErr] = useState("")

  useEffect(() => {
    if (!busy) return
    const t = setInterval(() => setStep((s) => (s + 1) % STEPS.length), 1100)
    return () => clearInterval(t)
  }, [busy])

  const valid = buyer.trim().length > 1 && Number(value) > 0 && (mode === "paste" ? text.trim().length > 40 : !!file)

  const run = async (e: React.FormEvent) => {
    e.preventDefault()
    setErr("")
    if (!valid) {
      setErr(
        mode === "paste"
          ? "Add a buyer name, a contract value and at least a paragraph of clause text."
          : "Add a buyer name, a contract value and choose a file.",
      )
      return
    }
    setBusy(true)
    setStep(0)
    setResult(null)
    try {
      const payload = { buyer_name: buyer.trim(), contract_value: Number(value), msme_type: msme }
      const report =
        mode === "upload" && file ? await analyseFile(file, payload) : await analyseText({ ...payload, message: text })
      setResult(report)
      setReport(report)
      toast(`Audit complete: ${report.violations?.length || 0} clauses flagged`, "success")
    } catch (e: any) {
      setErr(e?.message || "The audit could not be completed.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Contract auditor</p>
            <h1>Analyse a contract</h1>
            <p>
              Paste the clauses or upload the document. Every finding comes back with the MSMED Act section behind it,
              the rupee exposure and a replacement clause you can send.
            </p>
          </div>
          <div className="spacer" />
          <div className="seg">
            <button className={mode === "paste" ? "on" : ""} onClick={() => setMode("paste")}>Paste text</button>
            <button className={mode === "upload" ? "on" : ""} onClick={() => setMode("upload")}>Upload file</button>
          </div>
        </div>
      </div>

      <div className="grid g3">
        <Card className="g2">
          <CardHead
            title={mode === "paste" ? "Clause text" : "Contract document"}
            sub="Buyer name and contract value drive the interest and tax calculations."
            right={mode === "paste" ? <Button size="sm" onClick={() => setText(SAMPLE)}>Load sample</Button> : undefined}
          />
          <form className="stack" onSubmit={run}>
            {mode === "paste" ? (
              <Field label="Clauses" hint={`${text.trim().split(/\s+/).filter(Boolean).length} words`}>
                <textarea
                  className="textarea"
                  rows={11}
                  placeholder="Paste the payment, interest, dispute and cancellation clauses here"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                />
              </Field>
            ) : (
              <Dropzone file={file} onFile={setFile} />
            )}

            <div className="grid g3">
              <Field label="Buyer name">
                <input className="input" placeholder="Larsen Industrial Ltd" value={buyer} onChange={(e) => setBuyer(e.target.value)} />
              </Field>
              <Field label="Contract value" hint="in rupees">
                <input className="input" type="number" min={0} placeholder="1500000" value={value} onChange={(e) => setValue(e.target.value)} />
              </Field>
              <Field label="Enterprise class">
                <select className="select" value={msme} onChange={(e) => setMsme(e.target.value)}>
                  <option value="micro">Micro</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                </select>
              </Field>
            </div>

            {err && <div className="callout warn">{err}</div>}

            <div className="row" style={{ gap: 10 }}>
              <Button variant="primary" loading={busy} disabled={!valid && !busy}>
                {busy ? "Auditing" : "Run the audit"}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => {
                  setText("")
                  setFile(null)
                  setBuyer("")
                  setValue("")
                  setResult(null)
                  setErr("")
                }}
              >
                Clear
              </Button>
              {value && <span className="card-sub">Value on record: {inr(Number(value))}</span>}
            </div>

            {busy && (
              <div className="steps" style={{ marginTop: 6 }}>
                {STEPS.map((s, i) => (
                  <div key={s} className={`run-step ${i === step ? "active" : i < step ? "done" : ""}`}>
                    <span className="ring" />
                    {s}
                  </div>
                ))}
              </div>
            )}
          </form>
        </Card>

        <div className="stack">
          {result ? (
            <Card>
              <CardHead title="Result" sub={result.buyer_name} right={<Badge tone={riskTone(result.risk_level)}>{titleCase(result.risk_level)}</Badge>} />
              <div className="row" style={{ gap: 16, alignItems: "center", marginBottom: 14 }}>
                <ScoreRing score={result.compliance_score} label="score" />
                <div className="stack-sm" style={{ flex: 1 }}>
                  <Stat label="Clauses flagged" value={num(result.violations?.length)} />
                  <Stat label="Recoverable" value={inr(result.financial_summary?.total_recoverable, true)} tone="green" />
                </div>
              </div>
              <p className="card-sub" style={{ marginBottom: 14 }}>{result.overall_summary}</p>
              <Button block variant="primary" onClick={() => go("report", { id: result.report_id })}>Open the full report</Button>
            </Card>
          ) : (
            <Card soft>
              <CardHead title="What gets checked" sub="Five statutory tests on every clause" />
              <div className="stack-sm">
                {[
                  ["Payment cycle", "Section 15: anything beyond 45 days is unenforceable"],
                  ["Interest waiver", "Section 16: interest cannot be contracted away"],
                  ["Tax disallowance", "Section 43B(h): buyer loses the deduction"],
                  ["Dispute forum", "Samadhaan jurisdiction cannot be displaced"],
                  ["Unilateral cancellation", "One-sided termination and set-off rights"],
                ].map(([t, s]) => (
                  <div className="mini" key={t}>
                    <div className="k">{t}</div>
                    <div style={{ fontSize: 12.5, color: "var(--text-dim)", marginTop: 4, lineHeight: 1.5 }}>{s}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card soft>
            <CardHead title="Tip" sub="Faster auditing" />
            <p className="card-sub">
              Upload accepts PDF, DOCX and TXT. For scanned contracts, paste the payment and dispute clauses directly so
              the retriever has clean text to cite.
            </p>
          </Card>
        </div>
      </div>
    </>
  )
}
