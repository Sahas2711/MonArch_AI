import { create } from "zustand"
import type { AnalysisReport } from "../types"
import { navigate, onRouteChange, parseHash, routeById, type RouteId } from "../lib/router"
import {
  devLoginAllowed,
  getSession,
  initSession,
  loadAuthConfig,
  onSessionChange,
  signInAsDeveloper,
  signInWithPassword,
  signInWithToken,
  signOut as endSession,
  signUpWithPassword,
  type Role,
  type Session,
} from "../lib/session"

export type Route = RouteId

type Toast = { id: number; message: string; tone: "info" | "success" | "error" }

export type AuthResult = { ok: boolean; error?: string }

type State = {
  route: Route
  params: Record<string, string>
  theme: "light" | "dark"
  sidebarOpen: boolean
  paletteOpen: boolean
  session: Session | null
  signedIn: boolean
  email: string
  name: string
  userId: string
  role: Role
  authMode: "password" | "cognito" | "dev" | "none"
  intended: Route | null
  toasts: Toast[]
  report: AnalysisReport | null

  go: (route: Route, params?: Record<string, string>) => void
  toggleTheme: () => void
  setSidebar: (open: boolean) => void
  setPalette: (open: boolean) => void
  toast: (message: string, tone?: "info" | "success" | "error") => void
  dismissToast: (id: number) => void
  setReport: (report: AnalysisReport | null) => void

  signIn: (email: string, password: string) => Promise<AuthResult>
  signUp: (input: { email: string; password: string; fullName?: string; company?: string }) => Promise<AuthResult>
  signInToken: (token: string) => AuthResult
  signInDev: (email?: string) => AuthResult
  signOut: () => void
}

const ls = typeof localStorage !== "undefined" ? localStorage : null
const storedTheme = (ls?.getItem("monarch.theme") || ls?.getItem("wemboo.theme")) === "dark" ? "dark" : "light"

const booted = initSession()
loadAuthConfig()
const start = parseHash()

/* a signed-out visitor never lands on a protected screen, even by deep link */
const startRoute = (() => {
  const meta = routeById(start.id)
  if (meta.protected && !booted) return "signin" as RouteId
  if (meta.adminOnly && booted?.role !== "admin") return "dashboard" as RouteId
  return start.id
})()

export const useApp = create<State>((set, get) => ({
  route: startRoute,
  params: start.params,
  theme: storedTheme,
  sidebarOpen: false,
  paletteOpen: false,
  session: booted,
  signedIn: !!booted,
  email: booted?.email || "",
  name: booted?.name || "",
  userId: booted?.userId || "",
  role: booted?.role || "user",
  authMode: booted?.mode || "none",
  intended: startRoute === "signin" && start.id !== "signin" ? start.id : null,
  toasts: [],
  report: null,

  go: (route, params) => {
    const meta = routeById(route)
    if (meta.protected && !get().signedIn) {
      set({ intended: route, sidebarOpen: false, paletteOpen: false })
      navigate("signin")
      return
    }
    if (meta.adminOnly && get().role !== "admin") {
      get().toast("That screen needs the admin role.", "error")
      return
    }
    set({ sidebarOpen: false, paletteOpen: false })
    navigate(route, params)
  },

  toggleTheme: () => {
    const theme = get().theme === "dark" ? "light" : "dark"
    ls?.setItem("monarch.theme", theme)
    document.documentElement.setAttribute("data-theme", theme)
    set({ theme })
  },

  setSidebar: (sidebarOpen) => set({ sidebarOpen }),
  setPalette: (paletteOpen) => set({ paletteOpen }),

  toast: (message, tone = "info") => {
    const id = Date.now() + Math.random()
    set({ toasts: [...get().toasts, { id, message, tone }] })
    setTimeout(() => get().dismissToast(id), 4200)
  },

  dismissToast: (id) => set({ toasts: get().toasts.filter((t) => t.id !== id) }),
  setReport: (report) => set({ report }),

  /* ------------------------------------------------------- authentication */

  signIn: async (email, password) => {
    const res = await signInWithPassword(email, password)
    if (!res.ok) return { ok: false, error: res.error }
    const next = get().intended || "dashboard"
    set({ intended: null })
    navigate(next)
    return { ok: true }
  },

  signUp: async (input) => {
    const res = await signUpWithPassword(input)
    if (!res.ok) return { ok: false, error: res.error }
    set({ intended: null })
    navigate("dashboard")
    return { ok: true }
  },

  signInToken: (token) => {
    const res = signInWithToken(token)
    if (!res.ok) return { ok: false, error: res.error }
    const next = get().intended || "dashboard"
    set({ intended: null })
    navigate(next)
    return { ok: true }
  },

  signInDev: (email) => {
    if (!devLoginAllowed) {
      return { ok: false, error: "Local identities are disabled on this build. Use email and password." }
    }
    signInAsDeveloper(email)
    const next = get().intended || "dashboard"
    set({ intended: null })
    navigate(next)
    return { ok: true }
  },

  signOut: () => {
    endSession()
    navigate("landing")
  },
}))

/* keep the store in sync with the URL and the session */

onRouteChange((loc) => {
  const meta = routeById(loc.id)
  const { signedIn, role } = useApp.getState()

  if (meta.protected && !signedIn) {
    useApp.setState({ intended: loc.id, sidebarOpen: false, paletteOpen: false })
    navigate("signin", undefined, true)
    return
  }
  if (meta.adminOnly && role !== "admin") {
    navigate("dashboard", undefined, true)
    return
  }
  useApp.setState({ route: loc.id, params: loc.params, sidebarOpen: false, paletteOpen: false })
})

onSessionChange((s) => {
  const wasSignedIn = useApp.getState().signedIn
  useApp.setState({
    session: s,
    signedIn: !!s,
    email: s?.email || "",
    name: s?.name || "",
    userId: s?.userId || "",
    role: s?.role || "user",
    authMode: s?.mode || "none",
  })
  /* session ended (expired or signed out) while inside the product */
  if (wasSignedIn && !s) {
    const meta = routeById(useApp.getState().route)
    if (meta.protected) navigate("signin", undefined, true)
  }
})

export const currentSession = getSession
export const devLoginEnabled = devLoginAllowed
