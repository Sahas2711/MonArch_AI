import React, { useEffect, useMemo, useRef, useState } from "react"
import { useApp } from "../store/app"
import { Badge } from "./ui"
import { isOffline, onOfflineChange } from "../lib/api"
import { ROUTES, routeById, type RouteId } from "../lib/router"
import { expiresInLabel } from "../lib/session"

export const Logo: React.FC<{ onClick?: () => void; className?: string }> = ({ onClick, className = "" }) => (
  <button className={`logo ${className}`.trim()} onClick={onClick} aria-label="monarchAI home">
    <img src="/monarch-mark.png" alt="monarchAI" className="logo-mark-img" />
    <span className="logo-text">
      monarch<span className="logo-ai-accent">AI</span>
    </span>
  </button>
)

const SECTIONS: Array<"Workspace" | "Tools" | "Account"> = ["Workspace", "Tools", "Account"]

/* ------------------------------------------------------------- palette */

const Palette: React.FC = () => {
  const { paletteOpen, setPalette, go, toggleTheme, signOut, role } = useApp()
  const [q, setQ] = useState("")
  const [cursor, setCursor] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const commands = useMemo(() => {
    const nav = ROUTES.filter((r) => r.section !== "Marketing")
      .filter((r) => !r.adminOnly || role === "admin")
      .map((r) => ({ key: r.id, label: r.title, hint: r.blurb, group: r.section, run: () => go(r.id) }))
    return [
      ...nav,
      { key: "theme", label: "Switch colour theme", hint: "Light and dark", group: "Session", run: toggleTheme },
      { key: "home", label: "Open marketing site", hint: "Landing page", group: "Session", run: () => go("landing") },
      { key: "out", label: "Sign out", hint: "End this session", group: "Session", run: signOut },
    ]
  }, [go, role, signOut, toggleTheme])

  const filtered = commands.filter((c) => (q ? (c.label + c.hint).toLowerCase().includes(q.toLowerCase()) : true))

  useEffect(() => {
    if (paletteOpen) {
      setQ("")
      setCursor(0)
      setTimeout(() => inputRef.current?.focus(), 20)
    }
  }, [paletteOpen])

  if (!paletteOpen) return null

  return (
    <div className="palette-backdrop" onClick={() => setPalette(false)} role="presentation">
      <div className="palette" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="palette-input"
          placeholder="Jump to a screen or run a command"
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setCursor(0)
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setCursor(Math.min(cursor + 1, filtered.length - 1))
            if (e.key === "ArrowUp") setCursor(Math.max(cursor - 1, 0))
            if (e.key === "Escape") setPalette(false)
            if (e.key === "Enter") {
              filtered[cursor]?.run()
              setPalette(false)
            }
          }}
        />
        <div className="palette-list">
          {filtered.length === 0 && <div className="palette-empty">Nothing matches “{q}”</div>}
          {filtered.map((c, i) => (
            <button
              key={c.key}
              className={`palette-item ${i === cursor ? "on" : ""}`}
              onMouseEnter={() => setCursor(i)}
              onClick={() => {
                c.run()
                setPalette(false)
              }}
            >
              <span className="palette-label">{c.label}</span>
              <span className="palette-hint">{c.hint}</span>
              <span className="palette-group">{c.group}</span>
            </button>
          ))}
        </div>
        <div className="palette-foot">
          <span><kbd>↑</kbd><kbd>↓</kbd> move</span>
          <span><kbd>↵</kbd> open</span>
          <span><kbd>esc</kbd> close</span>
        </div>
      </div>
    </div>
  )
}

/* -------------------------------------------------------- account menu */

const AccountMenu: React.FC = () => {
  const { email, userId, role, authMode, session, go, signOut, theme, toggleTheme } = useApp()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onDoc)
    return () => document.removeEventListener("mousedown", onDoc)
  }, [])

  const initials = (email || userId).slice(0, 2).toUpperCase()

  return (
    <div className="acct" ref={ref}>
      <button className="acct-btn" onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="avatar-sm">{initials}</span>
        <span className="acct-meta">
          <span className="acct-email">{email || userId}</span>
          <span className="acct-role">{role.replace("_", " ")}</span>
        </span>
        <span aria-hidden="true">⌄</span>
      </button>
      {open && (
        <div className="acct-pop">
          <div className="acct-pop-head">
            <div className="acct-email">{email || "Unnamed session"}</div>
            <div className="acct-sub mono">{userId}</div>
            <div className="acct-sub">
              {authMode === "cognito" ? `Cognito token, ${expiresInLabel(session)}` : "Development identity, no token"}
            </div>
          </div>
          <button onClick={() => { setOpen(false); go("organization") }}>Organization and usage</button>
          <button onClick={() => { setOpen(false); go("billing") }}>Plans and billing</button>
          <button onClick={() => { setOpen(false); go("keys") }}>API keys</button>
          {role === "admin" && <button onClick={() => { setOpen(false); go("admin") }}>Administration</button>}
          <button onClick={toggleTheme}>{theme === "dark" ? "Light theme" : "Dark theme"}</button>
          <button className="danger-item" onClick={() => { setOpen(false); signOut() }}>Sign out</button>
        </div>
      )}
    </div>
  )
}

/* -------------------------------------------------------------- shell */

export const Shell: React.FC<React.PropsWithChildren<{ flush?: boolean }>> = ({ flush, children }) => {
  const { route, go, theme, toggleTheme, sidebarOpen, setSidebar, setPalette, role, report } = useApp()
  const [offline, setOfflineState] = useState(isOffline())

  useEffect(() => onOfflineChange(setOfflineState) as unknown as () => void, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setPalette(true)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [setPalette])

  const meta = routeById(route as RouteId)

  return (
    <div className="shell">
      {sidebarOpen && <div className="drawer-backdrop" onClick={() => setSidebar(false)} role="presentation" />}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="sb-head">
          <Logo onClick={() => go("landing")} />
        </div>

        <button className="sb-search" onClick={() => setPalette(true)}>
          <span>Search screens</span>
          <kbd>⌘K</kbd>
        </button>

        <nav className="sb-nav">
          {SECTIONS.map((section) => {
            const items = ROUTES.filter((r) => r.section === section).filter((r) => !r.adminOnly || role === "admin")
            if (!items.length) return null
            return (
              <div className="sb-group" key={section}>
                <div className="sb-label">{section}</div>
                {items.map((item) => (
                  <a
                    key={item.id}
                    className="sb-item"
                    href={`#${item.path}`}
                    aria-current={route === item.id}
                    onClick={(e) => {
                      e.preventDefault()
                      go(item.id)
                    }}
                  >
                    <span className="sb-ico" aria-hidden="true">{item.icon}</span>
                    <span className="sb-text">{item.title}</span>
                    {item.id === "report" && report && <span className="sb-pip" aria-hidden="true" />}
                  </a>
                ))}
              </div>
            )
          })}
        </nav>

        <div className="sb-foot">
          <AccountMenu />
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="icon-btn only-mobile" onClick={() => setSidebar(!sidebarOpen)} aria-label="Toggle navigation">≡</button>
          <nav className="crumbs" aria-label="Breadcrumb">
            <a href="#/dashboard" onClick={(e) => { e.preventDefault(); go("dashboard") }}>monarchAI</a>
            <span aria-hidden="true">/</span>
            <span className="crumb-sec">{meta.section}</span>
            <span aria-hidden="true">/</span>
            <span className="crumb-now">{meta.title}</span>
          </nav>
          <div className="spacer" />
          {offline && <Badge tone="orange" dot>Preview data, API unreachable</Badge>}
          <button className="icon-btn" onClick={() => setPalette(true)} aria-label="Open command palette">⌕</button>
          <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle colour theme">
            {theme === "dark" ? "◑" : "●"}
          </button>
        </header>
        <div className={`content ${flush ? "flush" : ""}`}>{children}</div>
      </div>

      <Palette />
    </div>
  )
}
