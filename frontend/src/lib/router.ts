/**
 * Hash router.
 *
 * Hash routing is used deliberately: FastAPI only serves the SPA shell on `/`,
 * `/app`, `/pricing` and `/workbench`, so path routing would 404 on refresh.
 * With hashes every screen is a real, shareable, refreshable URL and the
 * browser back/forward buttons work.
 */

export type RouteId =
  | "landing"
  | "signin"
  | "dashboard"
  | "analyze"
  | "report"
  | "history"
  | "negotiate"
  | "calculator"
  | "copilot"
  | "knowledge"
  | "organization"
  | "billing"
  | "keys"
  | "settings"
  | "admin"

export type RouteMeta = {
  id: RouteId
  path: string
  title: string
  section: "Marketing" | "Workspace" | "Tools" | "Account"
  protected: boolean
  adminOnly?: boolean
  icon: string
  blurb: string
}

export const ROUTES: RouteMeta[] = [
  { id: "landing", path: "/", title: "Home", section: "Marketing", protected: false, icon: "◆", blurb: "Product overview" },
  { id: "signin", path: "/signin", title: "Sign in", section: "Marketing", protected: false, icon: "⇥", blurb: "Authenticate" },
  { id: "dashboard", path: "/dashboard", title: "Dashboard", section: "Workspace", protected: true, icon: "▦", blurb: "Recovery position at a glance" },
  { id: "analyze", path: "/analyse", title: "Analyse contract", section: "Workspace", protected: true, icon: "⌁", blurb: "Audit a document or clause" },
  { id: "report", path: "/report", title: "Report", section: "Workspace", protected: true, icon: "☷", blurb: "Findings, exposure and drafts" },
  { id: "history", path: "/history", title: "Audit history", section: "Workspace", protected: true, icon: "↺", blurb: "Everything audited so far" },
  { id: "negotiate", path: "/negotiate", title: "Clause negotiator", section: "Tools", protected: true, icon: "⇄", blurb: "Rewrite a clause before signing" },
  { id: "calculator", path: "/calculator", title: "Interest calculator", section: "Tools", protected: true, icon: "₹", blurb: "Section 16 and 43B(h) maths" },
  { id: "copilot", path: "/copilot", title: "Copilot", section: "Tools", protected: true, icon: "✦", blurb: "Ask about MSME payment law" },
  { id: "knowledge", path: "/knowledge", title: "Knowledge base", section: "Tools", protected: true, icon: "◧", blurb: "Documents and memories" },
  { id: "organization", path: "/organization", title: "Organization", section: "Account", protected: true, icon: "○", blurb: "Members, usage, audit trail" },
  { id: "billing", path: "/pricing", title: "Plans and billing", section: "Account", protected: false, icon: "◑", blurb: "Compare plans, upgrade" },
  { id: "keys", path: "/api-keys", title: "API keys", section: "Account", protected: true, icon: "⚷", blurb: "Programmatic access" },
  { id: "settings", path: "/settings", title: "Settings", section: "Account", protected: true, icon: "⚒", blurb: "Profile, password, preferences" },
  { id: "admin", path: "/admin", title: "Administration", section: "Account", protected: true, adminOnly: true, icon: "⚙", blurb: "Tenants, health, erasure" },
]

export const routeById = (id: RouteId) => ROUTES.find((r) => r.id === id) as RouteMeta

export type Location = { id: RouteId; params: Record<string, string> }

export function parseHash(hash = window.location.hash): Location {
  const raw = (hash || "").replace(/^#/, "") || "/"
  const [pathPart, queryPart] = raw.split("?")
  const path = "/" + pathPart.replace(/^\/+|\/+$/g, "")
  const match = ROUTES.find((r) => r.path === (path === "/" ? "/" : path.toLowerCase()))
  const params: Record<string, string> = {}
  if (queryPart) new URLSearchParams(queryPart).forEach((v, k) => (params[k] = v))
  return { id: match?.id || "landing", params }
}

export function buildHash(id: RouteId, params?: Record<string, string>) {
  const path = routeById(id).path
  const qs = params && Object.keys(params).length ? "?" + new URLSearchParams(params).toString() : ""
  return `#${path}${qs}`
}

export function navigate(id: RouteId, params?: Record<string, string>, replace = false) {
  const target = buildHash(id, params)
  if (window.location.hash === target) return
  if (replace) history.replaceState(null, "", target)
  else window.location.hash = target
  if (replace) window.dispatchEvent(new HashChangeEvent("hashchange"))
}

export function onRouteChange(fn: (loc: Location) => void) {
  const handler = () => fn(parseHash())
  window.addEventListener("hashchange", handler)
  return () => window.removeEventListener("hashchange", handler)
}

export const goBack = () => history.back()
