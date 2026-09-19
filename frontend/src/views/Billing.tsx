import React, { useEffect, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Modal, Stat } from "../components/ui"
import { checkout, getUsage } from "../lib/api"
import { inr, num, titleCase } from "../lib/format"
import type { OrgUsage } from "../types"

const PLANS = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tagline: "Prove the exposure on your worst buyer.",
    limits: { analyses: 5, documents: 10, chat: 100, api: false },
  },
  {
    id: "pro",
    name: "Pro",
    price: 999,
    tagline: "For a finance team chasing receivables every week.",
    limits: { analyses: 50, documents: 100, chat: 1000, api: true },
    featured: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 4999,
    tagline: "Unlimited audits, API access and an audit trail your counsel will accept.",
    limits: { analyses: -1, documents: -1, chat: -1, api: true },
  },
]

const FEATURES: Array<[string, string, string, string]> = [
  ["Contract audits per cycle", "5", "50", "Unlimited"],
  ["Indexed documents", "10", "100", "Unlimited"],
  ["Copilot messages", "100", "1,000", "Unlimited"],
  ["Statutory interest maths", "yes", "yes", "yes"],
  ["Samadhaan complaint drafts", "yes", "yes", "yes"],
  ["Counter-clause drafting", "no", "yes", "yes"],
  ["API keys", "no", "yes", "yes"],
  ["Member roles and audit trail", "no", "yes", "yes"],
]

export const Billing: React.FC = () => {
  const { toast, go } = useApp()
  const [usage, setUsage] = useState<OrgUsage | null>(null)
  const [cycle, setCycle] = useState<"monthly" | "annual">("monthly")
  const [order, setOrder] = useState<any>(null)
  const [busy, setBusy] = useState("")

  useEffect(() => {
    getUsage().then(setUsage)
  }, [])

  const start = async (plan: string) => {
    setBusy(plan)
    const res = await checkout(plan)
    setBusy("")
    setOrder(res)
  }

  const priceOf = (p: number) => (cycle === "annual" ? Math.round(p * 10) : p)

  const current = usage?.plan || "free"

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Plans and billing</p>
            <h1>Pay for what you recover</h1>
            <p>One recovered invoice usually covers the year. Cancel whenever the receivables stop being a problem.</p>
          </div>
          <div className="spacer" />
          <div className="stack-sm" style={{ alignItems: "flex-end" }}>
            <div className="seg">
              <button className={cycle === "monthly" ? "on" : ""} onClick={() => setCycle("monthly")}>Monthly</button>
              <button className={cycle === "annual" ? "on" : ""} onClick={() => setCycle("annual")}>Annual</button>
            </div>
            <span className="plan-toggle-note">{cycle === "annual" ? "Two months free on annual" : "Billed each month"}</span>
          </div>
        </div>
      </div>

      {usage && (
        <div className="grid g4" style={{ marginBottom: 18 }}>
          <Stat label="Current plan" value={usage.limits.name} sub={usage.limits.price_inr ? `${inr(usage.limits.price_inr)} per month` : "No card on file"} />
          <Stat label="Audits used" value={`${num(usage.usage.analyses)} / ${usage.limits.analyses < 0 ? "\u221e" : num(usage.limits.analyses)}`} tone="orange" />
          <Stat label="Documents" value={`${num(usage.usage.documents)} / ${usage.limits.documents < 0 ? "\u221e" : num(usage.limits.documents)}`} />
          <Stat label="Copilot messages" value={`${num(usage.usage.chat_messages)} / ${usage.limits.chat_messages < 0 ? "\u221e" : num(usage.limits.chat_messages)}`} tone="green" />
        </div>
      )}

      <div className="grid g3" style={{ marginBottom: 20 }}>
        {PLANS.map((p) => (
          <div className={`plan-card ${p.featured ? "featured" : ""}`} key={p.id}>
            {p.featured && <span className="plan-tag">Most chosen</span>}
            <div className="plan-name">{p.name}</div>
            <div className="plan-price">
              {p.price === 0 ? "Free" : inr(priceOf(p.price))}
              {p.price > 0 && <span style={{ fontSize: 13, color: "var(--text-dim)", fontWeight: 500 }}>/{cycle === "annual" ? "year" : "month"}</span>}
            </div>
            <p className="card-sub" style={{ minHeight: 42 }}>{p.tagline}</p>
            <ul className="plan-features">
              <li>{p.limits.analyses < 0 ? "Unlimited" : p.limits.analyses} contract audits</li>
              <li>{p.limits.documents < 0 ? "Unlimited" : p.limits.documents} indexed documents</li>
              <li>{p.limits.chat < 0 ? "Unlimited" : num(p.limits.chat)} copilot messages</li>
              <li>{p.limits.api ? "API access included" : "No API access"}</li>
            </ul>
            {current === p.id ? (
              <Button block disabled>Current plan</Button>
            ) : p.price === 0 ? (
              <Button block variant="ghost" onClick={() => go("analyze")}>Start auditing</Button>
            ) : (
              <Button block variant={p.featured ? "primary" : "default"} loading={busy === p.id} onClick={() => start(p.id)}>
                Upgrade to {p.name}
              </Button>
            )}
          </div>
        ))}
      </div>

      <Card>
        <CardHead title="Compare in detail" sub="Every limit is enforced server side by the quota middleware." />
        <div className="table-wrap">
          <table className="table matrix">
            <thead>
              <tr>
                <th>Capability</th>
                <th>Free</th>
                <th>Pro</th>
                <th>Enterprise</th>
              </tr>
            </thead>
            <tbody>
              {FEATURES.map(([label, a, b, c]) => (
                <tr key={label}>
                  <td>{label}</td>
                  {[a, b, c].map((v, i) => (
                    <td key={i}>
                      {v === "yes" ? <span className="yes">\u2713</span> : v === "no" ? <span className="no">\u2014</span> : v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal
        open={!!order}
        title="Complete payment"
        onClose={() => setOrder(null)}
        footer={
          <>
            <Button onClick={() => setOrder(null)}>Close</Button>
            <Button
              variant="primary"
              onClick={() => {
                setOrder(null)
                toast("Razorpay checkout opens here once live keys are configured", "info")
              }}
            >
              Open Razorpay
            </Button>
          </>
        }
      >
        {order && (
          <div className="stack-sm">
            <div className="kv"><span>Plan</span><span>{titleCase(order.plan)}</span></div>
            <div className="kv"><span>Amount</span><span>{inr((order.amount || 0) / 100)}</span></div>
            <div className="kv"><span>Order</span><span className="mono">{order.order_id}</span></div>
            <div className="kv"><span>Key</span><span className="mono">{order.key_id}</span></div>
            <div className="callout">
              The server created this order through <span className="mono">POST /api/billing/checkout</span>. Payment
              confirmation arrives on the Razorpay webhook, so your plan flips once the signature is verified.
            </div>
          </div>
        )}
      </Modal>
    </>
  )
}
