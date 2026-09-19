import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, Empty, SkeletonRows } from "../components/ui"
import { listAnalyses } from "../lib/api"
import type { HistoryRow } from "../types"
import { dateTimeFmt, download, inr, num, riskTone, titleCase } from "../lib/format"

type SortKey = "created_at" | "buyer_name" | "compliance_score" | "violations_count" | "exposure"

const exposureOf = (r: HistoryRow) => r.report_data?.financial_summary?.total_financial_exposure || 0
const PAGE = 8

export const History: React.FC = () => {
  const { go, setReport, toast } = useApp()
  const [rows, setRows] = useState<HistoryRow[] | null>(null)
  const [q, setQ] = useState("")
  const [risk, setRisk] = useState("all")
  const [sort, setSort] = useState<SortKey>("created_at")
  const [dir, setDir] = useState<"asc" | "desc">("desc")
  const [page, setPage] = useState(0)
  const [open, setOpen] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setBusy(true)
    setRows(await listAnalyses())
    setBusy(false)
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = useMemo(() => {
    let list = rows || []
    const needle = q.trim().toLowerCase()
    if (needle) {
      list = list.filter((r) =>
        `${r.buyer_name} ${r.file_name} ${r.report_data?.overall_summary || ""}`.toLowerCase().includes(needle),
      )
    }
    if (risk !== "all") list = list.filter((r) => (r.report_data?.risk_level || "").toLowerCase() === risk)
    const mul = dir === "asc" ? 1 : -1
    return [...list].sort((a, b) => {
      switch (sort) {
        case "buyer_name":
          return a.buyer_name.localeCompare(b.buyer_name) * mul
        case "compliance_score":
          return ((a.compliance_score || 0) - (b.compliance_score || 0)) * mul
        case "violations_count":
          return ((a.violations_count || 0) - (b.violations_count || 0)) * mul
        case "exposure":
          return (exposureOf(a) - exposureOf(b)) * mul
        default:
          return (new Date(a.created_at).getTime() - new Date(b.created_at).getTime()) * mul
      }
    })
  }, [rows, q, risk, sort, dir])

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE))
  const view = filtered.slice(page * PAGE, page * PAGE + PAGE)

  const head = (key: SortKey, label: string) => (
    <th
      className="sortable"
      onClick={() => {
        if (sort === key) setDir(dir === "asc" ? "desc" : "asc")
        else {
          setSort(key)
          setDir("desc")
        }
        setPage(0)
      }}
    >
      {label}
      <span className="arrow">{sort === key ? (dir === "asc" ? "\u25b2" : "\u25bc") : "\u21c5"}</span>
    </th>
  )

  const exportCsv = () => {
    const header = "buyer,file,score,risk,violations,exposure,audited_at\n"
    const body = filtered
      .map((r) =>
        [
          `"${r.buyer_name}"`,
          `"${r.file_name}"`,
          r.compliance_score,
          r.report_data?.risk_level || "",
          r.violations_count,
          exposureOf(r),
          r.created_at,
        ].join(","),
      )
      .join("\n")
    download(`monarch-audit-history-${new Date().toISOString().slice(0, 10)}.csv`, header + body, "text/csv")
    toast(`Exported ${filtered.length} rows`, "success")
  }

  const openReport = (r: HistoryRow) => {
    setReport(r.report_data)
    go("report", { id: r.id })
  }

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Evidence trail</p>
            <h1>Audit history</h1>
            <p>Search, sort and re-open every audit. Export the whole filtered set for your finance team or counsel.</p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <Button size="sm" loading={busy} onClick={load}>Refresh</Button>
            <Button size="sm" variant="primary" onClick={exportCsv} disabled={!filtered.length}>Export CSV</Button>
          </div>
        </div>
      </div>

      <div className="toolbar">
        <input
          className="input search"
          placeholder="Search buyer, file or summary"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setPage(0)
          }}
        />
        <div className="chip-row">
          {["all", "critical", "high", "medium", "low"].map((r) => (
            <button
              key={r}
              className={`chip ${risk === r ? "on" : ""}`}
              onClick={() => {
                setRisk(r)
                setPage(0)
              }}
            >
              {titleCase(r)}
            </button>
          ))}
        </div>
        <span className="count-pill">{filtered.length} of {rows?.length || 0}</span>
      </div>

      <Card>
        {rows === null ? (
          <SkeletonRows rows={6} height={26} />
        ) : filtered.length === 0 ? (
          <Empty
            icon="\u21ba"
            title="Nothing matches those filters"
            hint="Clear the search or run a fresh audit to populate the trail."
            action={<Button variant="primary" size="sm" onClick={() => go("analyze")}>Analyse a contract</Button>}
          />
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    {head("buyer_name", "Buyer")}
                    {head("compliance_score", "Score")}
                    <th>Risk</th>
                    {head("violations_count", "Flags")}
                    {head("exposure", "Exposure")}
                    {head("created_at", "Audited")}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {view.map((r) => (
                    <React.Fragment key={r.id}>
                      <tr className="clickable" onClick={() => setOpen(open === r.id ? null : r.id)}>
                        <td>
                          <b>{r.buyer_name}</b>
                          <div className="card-sub">{r.file_name}</div>
                        </td>
                        <td><b style={{ fontVariantNumeric: "tabular-nums" }}>{r.compliance_score}</b>/100</td>
                        <td><Badge tone={riskTone(r.report_data?.risk_level)}>{titleCase(r.report_data?.risk_level)}</Badge></td>
                        <td>{num(r.violations_count)}</td>
                        <td>{inr(exposureOf(r), true)}</td>
                        <td>{dateTimeFmt(r.created_at)}</td>
                        <td style={{ textAlign: "right" }}>
                          <Button size="sm" onClick={(e) => { e.stopPropagation(); openReport(r) }}>Open</Button>
                        </td>
                      </tr>
                      {open === r.id && (
                        <tr className="row-sub">
                          <td colSpan={7}>
                            <div style={{ marginBottom: 10 }}>{r.report_data?.overall_summary}</div>
                            <div className="mini-grid">
                              {(r.report_data?.violations || []).slice(0, 4).map((v, i) => (
                                <div className="mini" key={i}>
                                  <div className="k">{titleCase(v.violation_type)}</div>
                                  <div className="v" style={{ fontSize: 13 }}>{v.cited_law}</div>
                                  <div style={{ marginTop: 6 }}>
                                    <Badge tone={riskTone(v.severity)}>{titleCase(v.severity)}</Badge>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            {pages > 1 && (
              <div className="row" style={{ marginTop: 14, gap: 8, alignItems: "center" }}>
                <Button size="sm" disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</Button>
                <span className="card-sub">Page {page + 1} of {pages}</span>
                <Button size="sm" disabled={page >= pages - 1} onClick={() => setPage(page + 1)}>Next</Button>
              </div>
            )}
          </>
        )}
      </Card>
    </>
  )
}
