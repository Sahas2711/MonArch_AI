import React, { useState } from "react"
import { useApp } from "../store/app"
import { Button } from "../components/ui"
import { Logo } from "../components/Shell"

const METRICS = [
  ["45 days", "Statutory payment ceiling"],
  ["3×", "RBI bank rate, compounded"],
  ["43B(h)", "Deduction the buyer loses"],
  ["< 60 sec", "Time to a full audit"],
]

const TRUST = ["Auto components", "Textiles & apparel", "Speciality chemicals", "IT services", "Packaging", "Engineering goods"]

const PRODUCTS = [
  { icon: "⌁", title: "Contract audit", body: "Clause extraction, policy rules and retrieval-grounded reasoning flag every term that conflicts with the MSMED Act — with the offending text quoted back to you.", link: "Run an audit", route: "analyze" },
  { icon: "₹", title: "Interest engine", body: "Compound interest with monthly rests at three times the RBI bank rate, plus the buyer's Section 43B(h) tax disallowance exposure.", link: "Open calculator", route: "calculator" },
  { icon: "⇄", title: "Clause negotiator", body: "Paste a draft clause before you sign and get an enforceable replacement with the commercial risk explained in plain language.", link: "Fix a clause", route: "negotiate" },
  { icon: "⚖", title: "Samadhaan drafting", body: "A structured Section 18 reference draft, generated only when a violation actually qualifies, ready for counsel review.", link: "See a report", route: "history" },
  { icon: "✦", title: "AI copilot", body: "A multi-agent system with routing, research, retrieval, reflection and vision — grounded in the documents you upload.", link: "Ask the copilot", route: "copilot" },
  { icon: "◉", title: "Review & audit trail", body: "Low-confidence findings are gated for human review, and every decision is written to an immutable organization trail.", link: "View organization", route: "organization" },
]

const STEPS = [
  { n: 1, t: "Upload the contract", d: "PDF, DOCX or pasted clause text, with the buyer name and contract value." },
  { n: 2, t: "Read the findings", d: "Every violation carries the statute, the evidence, the exposure and a compliant counter-clause." },
  { n: 3, t: "Escalate with confidence", d: "Follow the recovery ladder from demand letter to legal notice to a Samadhaan filing." },
]

const QUOTES = [
  { q: "We had eleven crore stuck in 90-day terms we had signed without reading. The audit priced the interest claim in a minute and the buyer settled in three weeks.", who: "Finance Controller", org: "Auto components, Pune", i: "FC" },
  { q: "The 43B(h) angle changed the conversation. Once the buyer's CFO saw the deduction was at risk, the payment cycle moved from 90 days to 45.", who: "Founder", org: "Speciality chemicals, Vapi", i: "FD" },
  { q: "Our counsel used to draft Samadhaan references from scratch. Now they review a draft that already cites the clause and the statute.", who: "Head of Legal", org: "Packaging group, Chennai", i: "HL" },
]

const FAQS = [
  { q: "What exactly does the audit check?", a: "Payment cycles against the 45-day ceiling under Section 15, interest waivers that are void under Section 16, Section 43B(h) tax disallowance triggers, dispute resolution clauses that bypass the Facilitation Council, and unfair terms such as unilateral cancellation." },
  { q: "How is the interest calculated?", a: "Compound interest with monthly rests at three times the RBI bank rate, applied from the deemed due date. Every step of the computation is shown so you can verify it before issuing a demand." },
  { q: "Is my contract data private?", a: "Documents and retrieval chunks are scoped to your user id and organization, and an administrator can erase all data for a user at any time from the admin console." },
  { q: "Can I use this through an API?", a: "Yes. On the Pro and Enterprise plans you can create API keys and call the audit endpoints directly from your ERP or accounting system." },
  { q: "Is this legal advice?", a: "No. monarchAI produces informational analysis and drafts for review. Findings that fall below the confidence threshold are flagged for human review, and drafts should be checked with counsel before filing." },
]

export const Landing: React.FC = () => {
  const { go } = useApp()
  const [open, setOpen] = useState<number | null>(0)

  return (
    <div className="lp">
      <nav className="lp-nav">
        <Logo onClick={() => go("landing")} />
        <div className="spacer" />
        <button className="nav-link" onClick={() => go("analyze")}>Audit</button>
        <button className="nav-link" onClick={() => go("calculator")}>Calculator</button>
        <button className="nav-link" onClick={() => go("copilot")}>Copilot</button>
        <button className="nav-link" onClick={() => go("billing")}>Pricing</button>
        <Button size="sm" variant="ghost" onClick={() => go("signin")}>Sign in</Button>
        <Button size="sm" variant="primary" onClick={() => go("dashboard")}>Open workspace</Button>
      </nav>

      <header className="hero">
        <span className="hero-badge"><span aria-hidden="true">●</span> MSMED Act compliance, on autopilot</span>
        <h1>Get paid on time, or <em>get paid with interest</em></h1>
        <p>
          monarchAI audits your supplier contracts against the MSMED Act, prices exactly what the delay is costing you, and
          drafts the paperwork to recover it — every finding traced back to statute.
        </p>
        <div className="hero-cta">
          <Button variant="primary" onClick={() => go("analyze")}>Analyse a contract free</Button>
          <Button onClick={() => go("copilot")}>Talk to the copilot</Button>
        </div>
        <div className="hero-note">No card required · 5 audits a month on the free tier</div>
      </header>

      <div className="metric-strip">
        {METRICS.map(([v, l]) => (
          <div className="metric" key={l}>
            <b>{v}</b>
            <span>{l}</span>
          </div>
        ))}
      </div>

      <div className="trust">
        <p>Built for Indian MSME suppliers across</p>
        <div className="trust-row">
          {TRUST.map((t) => <span className="trust-chip" key={t}>{t}</span>)}
        </div>
      </div>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">One platform</span>
          <h2>Everything the recovery workflow needs</h2>
          <p>From pre-signature clause review to a filed Section 18 reference, without leaving the workspace.</p>
        </div>
        <div className="grid g3">
          {PRODUCTS.map((f) => (
            <div className="feature-tile" key={f.title} role="button" tabIndex={0}
              onClick={() => go(f.route as any)}
              onKeyDown={(e) => e.key === "Enter" && go(f.route as any)}
              style={{ cursor: "pointer" }}>
              <div className="feature-ico" aria-hidden="true">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
              <span className="feature-tile-link">{f.link} →</span>
            </div>
          ))}
        </div>
      </section>

      <section className="band">
        <div className="split">
          <div>
            <span className="eyebrow">Know the number</span>
            <h2>See what one late invoice is really worth</h2>
            <p>
              The moment a payment crosses 45 days, statutory interest starts compounding and the buyer's tax deduction
              is at risk. We quantify both sides so you negotiate from a position of strength.
            </p>
            <ul className="check-list">
              <li>Compound interest with monthly rests at 3× the RBI bank rate</li>
              <li>Section 43B(h) disallowance exposure on the buyer's books</li>
              <li>Full calculation trail you can paste into a demand letter</li>
              <li>Escalation ladder that tracks each contact attempt</li>
            </ul>
            <div className="row wrap">
              <Button variant="primary" onClick={() => go("calculator")}>Open the calculator</Button>
              <Button onClick={() => go("analyze")}>Audit a contract</Button>
            </div>
          </div>
          <div className="mock" aria-hidden="true">
            <div className="mock-bar"><i /><i /><i /></div>
            <div className="mock-body">
              <div className="row">
                <strong style={{ fontSize: 15 }}>Buyer Enterprise Pvt Ltd</strong>
                <div className="spacer" />
                <span className="badge red">high risk</span>
              </div>
              <div className="grid g3" style={{ gap: 10 }}>
                <div className="stat pad-sm" style={{ padding: 12 }}>
                  <div className="k">Score</div><div className="v" style={{ fontSize: 20 }}>32</div>
                </div>
                <div className="stat" style={{ padding: 12 }}>
                  <div className="k">Interest</div><div className="v" style={{ fontSize: 20 }}>₹2.4L</div>
                </div>
                <div className="stat" style={{ padding: 12 }}>
                  <div className="k">Tax risk</div><div className="v" style={{ fontSize: 20 }}>₹3.8L</div>
                </div>
              </div>
              <div className="mock-row"><span>Payment cycle</span><span className="bar"><i style={{ width: "88%" }} /></span></div>
              <div className="mock-row"><span>Interest waiver</span><span className="bar"><i style={{ width: "72%" }} /></span></div>
              <div className="mock-row"><span>Dispute clause</span><span className="bar"><i style={{ width: "45%" }} /></span></div>
              <div className="quote-clause" style={{ fontSize: 12.5 }}>
                “Payment shall be released within ninety (90) days… no interest shall be payable.”
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">How it works</span>
          <h2>Three steps to a recoverable claim</h2>
        </div>
        <div className="grid g3">
          {STEPS.map((s) => (
            <div className="step-card" key={s.n}>
              <div className="step-n">{s.n}</div>
              <h3 style={{ marginBottom: 6 }}>{s.t}</h3>
              <p style={{ fontSize: 13.5, color: "var(--text-dim)", lineHeight: 1.65 }}>{s.d}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="band dark">
        <div className="section-head">
          <span className="eyebrow" style={{ background: "rgba(255,255,255,0.14)", color: "#fff" }}>Proof</span>
          <h2>Suppliers who stopped absorbing the delay</h2>
          <p>Every claim below started as a contract nobody had re-read since signing.</p>
        </div>
        <div className="grid g3">
          {QUOTES.map((t) => (
            <div className="quote-card" key={t.i}>
              <div className="stars" aria-hidden="true">★★★★★</div>
              <p>“{t.q}”</p>
              <div className="quote-who">
                <span className="avatar">{t.i}</span>
                <span><b>{t.who}</b><span>{t.org}</span></span>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <div className="section-head">
          <span className="eyebrow">FAQ</span>
          <h2>Questions finance teams ask first</h2>
        </div>
        <div className="faq">
          {FAQS.map((f, i) => (
            <div className="faq-item" key={f.q}>
              <button className="faq-q" aria-expanded={open === i} onClick={() => setOpen(open === i ? null : i)}>
                {f.q}<span className="sign" aria-hidden="true">{open === i ? "−" : "+"}</span>
              </button>
              {open === i && <div className="faq-a">{f.a}</div>}
            </div>
          ))}
        </div>
      </section>

      <section className="cta-band">
        <h2>See what one contract is costing you</h2>
        <p>Run a full MSMED Act audit in under a minute. Free tier, no card, no sales call.</p>
        <div className="hero-cta">
          <Button variant="primary" onClick={() => go("analyze")}>Start an audit</Button>
          <Button onClick={() => go("billing")}>Compare plans</Button>
        </div>
      </section>

      <footer className="lp-foot">
        <div className="foot-grid">
          <div>
            <Logo onClick={() => go("landing")} />
            <p style={{ marginTop: 12, fontSize: 13.5, maxWidth: "34ch" }}>
              MSMED Act compliance intelligence for Indian suppliers. Informational analysis, not legal advice.
            </p>
          </div>
          <div>
            <h4>Product</h4>
            <ul>
              <li><button onClick={() => go("analyze")}>Contract audit</button></li>
              <li><button onClick={() => go("negotiate")}>Clause negotiator</button></li>
              <li><button onClick={() => go("calculator")}>Interest calculator</button></li>
              <li><button onClick={() => go("copilot")}>AI copilot</button></li>
            </ul>
          </div>
          <div>
            <h4>Workspace</h4>
            <ul>
              <li><button onClick={() => go("dashboard")}>Dashboard</button></li>
              <li><button onClick={() => go("history")}>Audit history</button></li>
              <li><button onClick={() => go("knowledge")}>Knowledge base</button></li>
              <li><button onClick={() => go("organization")}>Organization</button></li>
            </ul>
          </div>
          <div>
            <h4>Developers</h4>
            <ul>
              <li><button onClick={() => go("keys")}>API keys</button></li>
              <li><button onClick={() => go("billing")}>Plans & billing</button></li>
              <li><button onClick={() => go("admin")}>Administration</button></li>
            </ul>
          </div>
        </div>
        <div className="row wrap">
          <span>© {new Date().getFullYear()} monarchAI</span>
          <div className="spacer" />
          <span>MSMED Act 2006 · Sections 15, 16, 18 · Income Tax Act 43B(h)</span>
        </div>
      </footer>
    </div>
  )
}
