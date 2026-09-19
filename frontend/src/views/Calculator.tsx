import React, { useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Field, Stat } from "../components/ui"
import { copyText, download, inr, num, statutoryInterest, taxDisallowance } from "../lib/format"

const PRESETS: Array<[string, number, number]> = [
  ["Small invoice, 3 months late", 250000, 3],
  ["Typical tier-1 delay", 1500000, 6],
  ["Year-old receivable", 4000000, 12],
  ["Chronic default", 9000000, 24],
]

export const Calculator: React.FC = () => {
  const { toast, go } = useApp()
  const [principal, setPrincipal] = useState(1500000)
  const [months, setMonths] = useState(6)
  const [bankRate, setBankRate] = useState(6.5)
  const [taxRate, setTaxRate] = useState(25)

  const result = useMemo(() => statutoryInterest(principal, months, bankRate), [principal, months, bankRate])
  const tax = useMemo(() => taxDisallowance(principal, taxRate), [principal, taxRate])

  const schedule = useMemo(() => {
    const rows: Array<{ m: number; opening: number; interest: number; closing: number }> = []
    let opening = principal
    const rate = (bankRate * 3) / 12 / 100
    for (let m = 1; m <= Math.min(months, 36); m++) {
      const interest = opening * rate
      const closing = opening + interest
      rows.push({ m, opening, interest, closing })
      opening = closing
    }
    return rows
  }, [principal, months, bankRate])

  const maxClosing = Math.max(principal, ...schedule.map((r) => r.closing))

  const exportCsv = () => {
    const csv =
      "month,opening,interest,closing\n" +
      schedule.map((r) => [r.m, r.opening.toFixed(2), r.interest.toFixed(2), r.closing.toFixed(2)].join(",")).join("\n")
    download(`statutory-interest-${principal}-${months}m.csv`, csv, "text/csv")
    toast("Schedule exported", "success")
  }

  const summary = `Principal ${inr(principal)}\nDelay ${months} months\nStatutory rate ${result.annualRate}% per year, compounded monthly\nInterest ${inr(result.interest)}\nTotal recoverable ${inr(result.totalRecoverable)}\nBuyer tax disallowance under 43B(h) ${inr(tax)}`

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Section 16 and 43B(h)</p>
            <h1>Interest calculator</h1>
            <p>Three times the RBI bank rate, compounded with monthly rests, plus the deduction the buyer loses until they pay.</p>
          </div>
          <div className="spacer" />
          <Badge tone="blue" dot>{result.annualRate}% per year</Badge>
        </div>
      </div>

      <div className="grid g3">
        <Card className="g2">
          <CardHead title="Your receivable" sub="Drag or type. Everything recalculates instantly." />
          <div className="chip-row" style={{ marginBottom: 18 }}>
            {PRESETS.map(([label, p, m]) => (
              <button
                key={label}
                className={`chip ${principal === p && months === m ? "on" : ""}`}
                onClick={() => {
                  setPrincipal(p)
                  setMonths(m)
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="stack">
            <Field label="Principal outstanding" hint={inr(principal)}>
              <input type="range" min={25000} max={20000000} step={25000} value={principal} onChange={(e) => setPrincipal(Number(e.target.value))} />
            </Field>
            <div className="grid g3">
              <Field label="Amount" hint="rupees">
                <input className="input" type="number" min={0} value={principal} onChange={(e) => setPrincipal(Number(e.target.value) || 0)} />
              </Field>
              <Field label="Months overdue" hint="beyond the 45 day window">
                <input className="input" type="number" min={0} max={120} value={months} onChange={(e) => setMonths(Number(e.target.value) || 0)} />
              </Field>
              <Field label="RBI bank rate" hint="percent">
                <input className="input" type="number" step={0.25} min={0} value={bankRate} onChange={(e) => setBankRate(Number(e.target.value) || 0)} />
              </Field>
            </div>
            <Field label="Months overdue" hint={`${months} months`}>
              <input type="range" min={0} max={36} value={months} onChange={(e) => setMonths(Number(e.target.value))} />
            </Field>
            <Field label="Buyer's tax rate" hint={`${taxRate}% used for the 43B(h) estimate`}>
              <input type="range" min={10} max={40} value={taxRate} onChange={(e) => setTaxRate(Number(e.target.value))} />
            </Field>
          </div>

          <h3 style={{ margin: "22px 0 6px", fontSize: 15 }}>Balance with monthly rests</h3>
          <div className="bars">
            {schedule.slice(-12).map((r) => (
              <div className="col" key={r.m} title={`Month ${r.m}: ${inr(r.closing)}`}>
                <div className="bar" style={{ height: `${(r.closing / maxClosing) * 100}%` }} />
                <span className="cap">M{r.m}</span>
              </div>
            ))}
          </div>

          {schedule.length > 0 && (
            <div className="table-wrap" style={{ marginTop: 18 }}>
              <table className="table">
                <thead><tr><th>Month</th><th>Opening</th><th>Interest</th><th>Closing</th></tr></thead>
                <tbody>
                  {schedule.map((r) => (
                    <tr key={r.m}>
                      <td>{r.m}</td>
                      <td>{inr(r.opening)}</td>
                      <td style={{ color: "var(--orange)" }}>{inr(r.interest)}</td>
                      <td><b>{inr(r.closing)}</b></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="stack sticky-side">
          <Card>
            <CardHead title="What you can claim" sub="Compounded monthly, not simple" />
            <div className="stack-sm">
              <Stat label="Statutory interest" value={inr(result.interest)} sub={`${result.monthlyRate.toFixed(3)}% per month`} tone="orange" />
              <Stat label="Total recoverable" value={inr(result.totalRecoverable)} sub={`Principal ${inr(principal)}`} tone="green" />
              <Stat label="Buyer's lost deduction" value={inr(tax)} sub={`Section 43B(h) at ${taxRate}%`} tone="red" />
              <Stat label="Uplift on principal" value={`${principal ? ((result.interest / principal) * 100).toFixed(1) : "0"}%`} sub={`Over ${num(months)} months`} />
            </div>
            <div className="row" style={{ gap: 8, marginTop: 14, flexWrap: "wrap" }}>
              <Button size="sm" onClick={async () => toast((await copyText(summary)) ? "Summary copied" : "Copy blocked", "success")}>Copy summary</Button>
              <Button size="sm" onClick={exportCsv}>Export CSV</Button>
            </div>
          </Card>

          <Card soft>
            <CardHead title="Use it in a demand letter" sub="Wording that tends to land" />
            <div className="pre" style={{ whiteSpace: "pre-wrap" }}>{`Our invoice remains unpaid ${months} months beyond the statutory 45 day window under Section 15 of the MSMED Act, 2006. Interest of ${inr(result.interest)} has accrued at ${result.annualRate}% per annum, compounded with monthly rests, under Section 16. The total amount now payable is ${inr(result.totalRecoverable)}. Please also note that the expense stands disallowed under Section 43B(h) of the Income Tax Act until payment is made.`}</div>
            <Button size="sm" style={{ marginTop: 12 }} onClick={() => go("analyze")}>Audit the contract too</Button>
          </Card>
        </div>
      </div>
    </>
  )
}
