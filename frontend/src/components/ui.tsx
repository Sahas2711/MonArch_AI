import React, { useEffect, useState } from "react"
import { useApp } from "../store/app"

type Tone = "gray" | "blue" | "green" | "orange" | "red" | "purple"

export const Card: React.FC<React.PropsWithChildren<{ soft?: boolean; className?: string; style?: React.CSSProperties }>> = ({
  soft,
  className = "",
  style,
  children,
}) => (
  <div className={`card ${soft ? "soft" : ""} ${className}`} style={style}>
    {children}
  </div>
)

export const CardHead: React.FC<{ title: string; sub?: string; right?: React.ReactNode }> = ({ title, sub, right }) => (
  <div className="card-head">
    <div style={{ flex: 1, minWidth: 0 }}>
      <h3>{title}</h3>
      {sub && <div className="card-sub" style={{ marginTop: 4 }}>{sub}</div>}
    </div>
    {right}
  </div>
)

export const Badge: React.FC<React.PropsWithChildren<{ tone?: Tone; dot?: boolean }>> = ({ tone = "gray", dot, children }) => (
  <span className={`badge ${tone === "gray" ? "" : tone}`}>
    {dot && <span className="dot" />}
    {children}
  </span>
)

export const Spinner: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={{ animation: "spin 0.8s linear infinite" }}>
    <style>{"@keyframes spin{to{transform:rotate(360deg)}}"}</style>
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" fill="none" opacity="0.25" />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" />
  </svg>
)

export const Button: React.FC<
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "default" | "primary" | "danger" | "ghost"
    size?: "md" | "sm"
    block?: boolean
    loading?: boolean
  }
> = ({ variant = "default", size = "md", block, loading, children, className = "", disabled, ...rest }) => (
  <button
    className={`btn ${variant === "default" ? "" : variant} ${size === "sm" ? "sm" : ""} ${block ? "block" : ""} ${className}`}
    disabled={disabled || loading}
    {...rest}
  >
    {loading && <Spinner />}
    {children}
  </button>
)

export const Field: React.FC<{ label: string; hint?: string; children: React.ReactNode }> = ({ label, hint, children }) => (
  <label className="field">
    <span>
      {label} {hint && <span className="hint">{hint}</span>}
    </span>
    {children}
  </label>
)

export const Stat: React.FC<{ label: string; value: React.ReactNode; sub?: string; tone?: Tone }> = ({ label, value, sub, tone }) => (
  <div className="stat">
    <div className="k">{label}</div>
    <div className="v" style={tone && tone !== "gray" ? { color: `var(--${tone === "blue" ? "accent" : tone})` } : undefined}>
      {value}
    </div>
    {sub && <div className="s">{sub}</div>}
  </div>
)

export const Empty: React.FC<{ icon?: string; title: string; hint?: string; action?: React.ReactNode }> = ({
  icon = "○",
  title,
  hint,
  action,
}) => (
  <div className="empty">
    <div className="em-ico" aria-hidden="true">{icon}</div>
    <div style={{ fontWeight: 600, color: "var(--text)" }}>{title}</div>
    {hint && <div style={{ marginTop: 6, maxWidth: 420, marginInline: "auto" }}>{hint}</div>}
    {action && <div style={{ marginTop: 16 }}>{action}</div>}
  </div>
)

export const Progress: React.FC<{ value: number; tone?: Tone }> = ({ value, tone = "blue" }) => (
  <div className="progress">
    <span style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: `var(--${tone === "blue" ? "accent" : tone})` }} />
  </div>
)

export const ScoreRing: React.FC<{ score: number; size?: number; label?: string }> = ({ score, size = 96, label }) => {
  const tone = score >= 70 ? "var(--green)" : score >= 40 ? "var(--orange)" : "var(--red)"
  const r = (size - 12) / 2
  const c = 2 * Math.PI * r
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} role="img" aria-label={`Compliance score ${score} out of 100`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-2)" strokeWidth="8" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={tone}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${(c * score) / 100} ${c}`}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", lineHeight: 1.1 }}>
        <span style={{ fontSize: size * 0.28, fontWeight: 600, letterSpacing: "-0.02em" }}>{score}</span>
        {label && <span style={{ fontSize: 10, color: "var(--text-dim)", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</span>}
      </div>
    </div>
  )
}

export const Modal: React.FC<
  React.PropsWithChildren<{ open: boolean; title: string; onClose: () => void; footer?: React.ReactNode; wide?: boolean }>
> = ({ open, title, onClose, footer, wide, children }) => {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div className="modal" style={wide ? { maxWidth: 760 } : undefined} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h3 style={{ flex: 1 }}>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close dialog">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  )
}

export const Toaster: React.FC = () => {
  const toasts = useApp((s) => s.toasts)
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.tone === "error" ? "error" : t.tone === "success" ? "success" : ""}`}>
          {t.message}
        </div>
      ))}
    </div>
  )
}

export const Accordion: React.FC<{ header: React.ReactNode; defaultOpen?: boolean; children: React.ReactNode }> = ({
  header,
  defaultOpen,
  children,
}) => {
  const [open, setOpen] = useState(!!defaultOpen)
  return (
    <div className="accordion-item">
      <button className="accordion-btn" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span aria-hidden="true" style={{ color: "var(--text-dim)", transform: open ? "rotate(90deg)" : "none", transition: "transform .15s" }}>
          ▸
        </span>
        <span style={{ flex: 1, minWidth: 0 }}>{header}</span>
      </button>
      {open && <div className="accordion-panel">{children}</div>}
    </div>
  )
}

export const Dropzone: React.FC<{ file: File | null; onFile: (f: File | null) => void; accept?: string; hint?: string }> = ({
  file,
  onFile,
  accept = ".pdf,.docx,.txt",
  hint = "PDF, DOCX or TXT up to 10 MB",
}) => {
  const [over, setOver] = useState(false)
  const inputRef = React.useRef<HTMLInputElement | null>(null)
  return (
    <div
      className={`dropzone ${over ? "over" : ""}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault()
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        onFile(e.dataTransfer.files?.[0] || null)
      }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept={accept} hidden onChange={(e) => onFile(e.target.files?.[0] || null)} />
      {file ? (
        <div>
          <div style={{ fontWeight: 600 }}>{file.name}</div>
          <div style={{ fontSize: 12.5, color: "var(--text-dim)", marginTop: 4 }}>
            {(file.size / 1024).toFixed(0)} KB · click to replace
          </div>
        </div>
      ) : (
        <div>
          <div style={{ fontSize: 22, marginBottom: 8, opacity: 0.6 }} aria-hidden="true">↑</div>
          <div style={{ fontWeight: 600 }}>Drop a contract here, or click to browse</div>
          <div style={{ fontSize: 12.5, color: "var(--text-dim)", marginTop: 4 }}>{hint}</div>
        </div>
      )}
    </div>
  )
}

export const Sparkline: React.FC<{ points: number[]; labels?: string[]; height?: number }> = ({
  points,
  labels,
  height = 140,
}) => {
  if (!points.length) return null
  const w = 600
  const max = Math.max(100, ...points)
  const min = Math.min(0, ...points)
  const step = points.length > 1 ? w / (points.length - 1) : w
  const y = (v: number) => height - 20 - ((v - min) / Math.max(1, max - min)) * (height - 40)
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${i * step},${y(p)}`).join(" ")
  const area = `${path} L${(points.length - 1) * step},${height} L0,${height} Z`
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${height}`} width="100%" height={height} role="img" aria-label="Compliance score trend">
        <defs>
          <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#spark)" />
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <circle key={i} cx={i * step} cy={y(p)} r="3.5" fill="var(--canvas)" stroke="var(--accent)" strokeWidth="2" />
        ))}
      </svg>
      {labels && (
        <div className="row" style={{ fontSize: 12, color: "var(--text-dim)" }}>
          <span>{labels[0]}</span>
          <div className="spacer" />
          <span>{labels[1]}</span>
        </div>
      )}
    </div>
  )
}

export const KV: React.FC<{ k: string; v: React.ReactNode }> = ({ k, v }) => (
  <div className="kv">
    <span className="k">{k}</span>
    <span className="v">{v}</span>
  </div>
)

export const SkeletonRows: React.FC<{ rows?: number; height?: number }> = ({ rows = 3, height = 52 }) => (
  <div className="stack-sm">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="skel" style={{ height }} />
    ))}
  </div>
)
