import React, { useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Empty, Field } from "../components/ui"
import { negotiate } from "../lib/api"
import { copyText, download, pct, titleCase } from "../lib/format"
import type { NegotiationRecommendation } from "../types"

const EXAMPLES: Array<[string, string]> = [
  ["120 day payment", "Payment shall be made within 120 days from the date of receipt of invoice."],
  ["Interest waiver", "The Supplier waives any claim to interest on delayed payments."],
  ["Foreign arbitration", "All disputes shall be referred to arbitration seated in Singapore."],
  ["Unilateral set-off", "The Buyer may set off any amounts at its sole discretion without notice."],
]

export const Negotiate: React.FC = () => {
  const { toast, go } = useApp()
  const [clause, setClause] = useState("")
  const [buyer, setBuyer] = useState("")
  const [value, setValue] = useState("")
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState<NegotiationRecommendation[] | null>(null)

  const run = async (e: React.FormEvent) => {
    e.preventDefault()
    if (clause.trim().length < 15) {
      toast("Paste the full clause so the statute match is reliable", "error")
      return
    }
    setBusy(true)
    const res = await negotiate(clause.trim(), buyer.trim() || undefined, value ? Number(value) : undefined)
    setResults(res)
    setBusy(false)
    toast(res.length ? `${res.length} replacement${res.length > 1 ? "s" : ""} drafted` : "No breach detected in that clause", res.length ? "success" : "info")
  }

  const copy = async (text: string) => {
    toast((await copyText(text)) ? "Replacement copied" : "Copy blocked by the browser", "success")
  }

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Pre-signature defence</p>
            <h1>Clause negotiator</h1>
            <p>Paste a clause from a draft contract. You get the breach, the statute behind it and wording you can send back the same day.</p>
          </div>
          <div className="spacer" />
          <Button size="sm" onClick={() => go("analyze")}>Audit a whole contract</Button>
        </div>
      </div>

      <div className="grid g3">
        <Card className="g2">
          <CardHead title="Clause under review" sub="One clause at a time gives the cleanest citation." />
          <form className="stack" onSubmit={run}>
            <div className="chip-row">
              {EXAMPLES.map(([label, text]) => (
                <button type="button" className="chip" key={label} onClick={() => setClause(text)}>{label}</button>
              ))}
            </div>
            <Field label="Clause text" hint={`${clause.trim().length} characters`}>
              <textarea
                className="textarea"
                rows={7}
                placeholder="Payment shall be made within 120 days..."
                value={clause}
                onChange={(e) => setClause(e.target.value)}
              />
            </Field>
            <div className="grid g2">
              <Field label="Buyer" hint="optional">
                <input className="input" value={buyer} onChange={(e) => setBuyer(e.target.value)} placeholder="Larsen Industrial Ltd" />
              </Field>
              <Field label="Contract value" hint="optional, sharpens the exposure note">
                <input className="input" type="number" min={0} value={value} onChange={(e) => setValue(e.target.value)} placeholder="1500000" />
              </Field>
            </div>
            <div className="row" style={{ gap: 10 }}>
              <Button variant="primary" loading={busy}>Draft a compliant version</Button>
              <Button type="button" variant="ghost" onClick={() => { setClause(""); setResults(null) }}>Clear</Button>
            </div>
          </form>
        </Card>

        <Card soft className="sticky-side">
          <CardHead title="Why this works" sub="Three non-negotiables" />
          <ul className="check-list">
            <li>A payment window beyond 45 days is unenforceable against a registered micro or small enterprise.</li>
            <li>Interest under Section 16 is statutory. A waiver clause does not bind you.</li>
            <li>Samadhaan jurisdiction survives any arbitration or foreign-seat clause.</li>
          </ul>
          <p className="card-sub" style={{ marginTop: 12 }}>
            Replacement wording is drafted to be commercially acceptable, not aggressive, so buyers sign it.
          </p>
        </Card>
      </div>

      <div style={{ marginTop: 18 }}>
        {results === null ? null : results.length === 0 ? (
          <Empty icon="\u2713" title="No statutory breach found" hint="That clause reads as compliant. Try another one, or audit the full contract." />
        ) : (
          <div className="stack">
            {results.map((r, i) => (
              <Card key={i}>
                <CardHead
                  title={titleCase(r.violation_type)}
                  sub={r.cited_law}
                  right={
                    <div className="row" style={{ gap: 8 }}>
                      <Badge tone="blue">Confidence {pct(r.confidence)}</Badge>
                      <Button size="sm" onClick={() => copy(r.compliant_replacement)}>Copy</Button>
                      <Button size="sm" variant="ghost" onClick={() => download(`clause-${i + 1}.txt`, r.compliant_replacement)}>Download</Button>
                    </div>
                  }
                />
                <div className="diff">
                  <div className="diff-col bad"><div className="dh">Their wording</div><div className="db">{r.original_clause}</div></div>
                  <div className="diff-col good"><div className="dh">Your counter-clause</div><div className="db">{r.compliant_replacement}</div></div>
                </div>
                <div className="callout" style={{ marginTop: 12 }}>{r.risk_explanation}</div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  )
}
