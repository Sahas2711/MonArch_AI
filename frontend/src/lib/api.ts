import type {
  AnalysisReport,
  ApiKey,
  ChatResponse,
  ContactActionResponse,
  HealthResponse,
  HistoryRow,
  NegotiationRecommendation,
  Organization,
  OrgUsage,
} from "../types"
import {
  demoDocuments,
  demoHealth,
  demoHistory,
  demoKeys,
  demoMemories,
  demoNegotiation,
  demoReport,
  demoUsage,
} from "./demo"

export const API_BASE = (import.meta as any).env?.VITE_API_BASE || ""

const TOKEN_KEY = "monarch.token"
const USER_KEY = "monarch.user"
const ls = typeof localStorage !== "undefined" ? localStorage : null

export const auth = {
  token: ls?.getItem(TOKEN_KEY) || ls?.getItem("wemboo.token") || "",
  userId: ls?.getItem(USER_KEY) || ls?.getItem("wemboo.user") || "dev_user_123",
  set(token: string, userId?: string) {
    auth.token = token
    ls?.setItem(TOKEN_KEY, token)
    if (userId) {
      auth.userId = userId
      ls?.setItem(USER_KEY, userId)
    }
  },
  clear() {
    auth.token = ""
    auth.userId = "dev_user_123"
    ls?.removeItem(TOKEN_KEY)
    ls?.removeItem(USER_KEY)
  },
}

const headers = (json = true): Record<string, string> => {
  const h: Record<string, string> = {}
  if (json) h["Content-Type"] = "application/json"
  if (auth.token) h["Authorization"] = `Bearer ${auth.token}`
  return h
}

let offline = false
const listeners = new Set<(v: boolean) => void>()
const setOffline = (v: boolean) => {
  if (offline === v) return
  offline = v
  listeners.forEach((fn) => fn(v))
}
export const isOffline = () => offline
export const onOfflineChange = (fn: (v: boolean) => void) => {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      detail = body?.detail || body?.message || detail
    } catch {
      /* ignore */
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status)
  }
  setOffline(false)
  const text = await res.text()
  return (text ? JSON.parse(text) : null) as T
}

async function withFallback<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn()
  } catch (e) {
    if (e instanceof ApiError && e.status !== 0 && e.status < 500 && e.status !== 404) throw e
    setOffline(true)
    return fallback
  }
}

/* ---------------------------------------------------------------- health */

export const getHealth = () => withFallback(() => request<HealthResponse>("/api/health"), demoHealth)

/* -------------------------------------------------------------- analysis */

type AnalysePayload = { message?: string; buyer_name: string; contract_value: number; msme_type: string }

export const analyseText = (payload: AnalysePayload) =>
  withFallback(
    () => request<AnalysisReport>("/api/analyse", { method: "POST", headers: headers(), body: JSON.stringify(payload) }),
    { ...demoReport, buyer_name: payload.buyer_name },
  )

export const analyseFile = (file: File, payload: AnalysePayload) => {
  const fd = new FormData()
  fd.append("file", file)
  fd.append("buyer_name", payload.buyer_name)
  fd.append("contract_value", String(payload.contract_value))
  fd.append("msme_type", payload.msme_type)
  return withFallback(
    () => request<AnalysisReport>("/api/analyse", { method: "POST", headers: headers(false), body: fd }),
    { ...demoReport, buyer_name: payload.buyer_name, file_name: file.name },
  )
}

export const listAnalyses = () =>
  withFallback(async () => {
    const res = await request<any>("/api/analyses", { headers: headers() })
    return (Array.isArray(res) ? res : res?.analyses || []) as HistoryRow[]
  }, demoHistory)

export const getAnalysis = (reportId: string) =>
  withFallback(() => request<AnalysisReport>(`/api/analyses/${reportId}`, { headers: headers() }), demoReport)

export const reviewAnalysis = (
  reportId: string,
  body: { action: string; reviewer_name?: string; notes?: string; modified_violations?: unknown[] },
) =>
  withFallback(
    () =>
      request<AnalysisReport>(`/api/analyses/${reportId}/review`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify(body),
      }),
    {
      ...demoReport,
      review_decision: {
        ...(demoReport.review_decision as any),
        needs_human_review: false,
        auto_approved: body.action === "approved",
        recommended_action: body.action,
      },
    },
  )

export const recordContact = (reportId: string) =>
  withFallback(
    () => request<ContactActionResponse>(`/api/analyses/${reportId}/contact`, { method: "POST", headers: headers() }),
    {
      report_id: reportId,
      contact_attempts: (demoReport.contact_attempts || 0) + 1,
      first_contact_date: demoReport.first_contact_date,
      recommended_actions: demoReport.recommended_actions || [],
    },
  )

export const negotiate = (clause_text: string, buyer_name?: string, contract_value?: number) =>
  withFallback(async () => {
    const res = await request<any>("/api/negotiate", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ clause_text, buyer_name, contract_value }),
    })
    return (Array.isArray(res) ? res : res?.recommendations || []) as NegotiationRecommendation[]
  }, demoNegotiation)

/* ------------------------------------------------------------------ chat */

export type ChatPayload = {
  user_inp: string
  user_id?: string
  chat_id?: string
  image_data?: string | null
  eval_response?: boolean
}

export const chat = (payload: ChatPayload) =>
  request<ChatResponse>("/api/chat", { method: "POST", headers: headers(), body: JSON.stringify(payload) })

export async function streamChat(
  payload: ChatPayload,
  handlers: {
    onRoute?: (route: string, chatId: string) => void
    onToken?: (token: string) => void
    onDone?: (output: string, route: string, chatId: string) => void
    onError?: (detail: string) => void
  },
  signal?: AbortSignal,
) {
  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
      signal,
    })
    if (!res.ok || !res.body) throw new Error(`Stream failed (${res.status})`)
    setOffline(false)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let route = ""
    let chatId = payload.chat_id || ""

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split("\n\n")
      buffer = parts.pop() || ""
      for (const part of parts) {
        for (const line of part.split("\n")) {
          const trimmed = line.trim()
          if (!trimmed.startsWith("data:")) continue
          const raw = trimmed.slice(5).trim()
          if (!raw || raw === "[DONE]") continue
          let data: any
          try {
            data = JSON.parse(raw)
          } catch {
            continue
          }
          switch (data.event) {
            case "route":
              route = data.route || data.data || route
              chatId = data.chat_id || chatId
              handlers.onRoute?.(route, chatId)
              break
            case "token":
              handlers.onToken?.(data.token ?? data.data ?? "")
              break
            case "done":
              handlers.onDone?.(data.output ?? "", data.route ?? route, data.chat_id ?? chatId)
              return
            case "error":
              handlers.onError?.(data.detail || data.error || "Stream error")
              return
            default:
              if (typeof data.token === "string") handlers.onToken?.(data.token)
          }
        }
      }
    }
    handlers.onDone?.("", route, chatId)
  } catch (e: any) {
    if (e?.name === "AbortError") return
    setOffline(true)
    const demo =
      "I could not reach the backend, so here is a general answer. Under Section 15 of the MSMED Act a buyer must pay a registered micro or small enterprise within 45 days of acceptance. Delay attracts compound interest with monthly rests at three times the RBI bank rate under Section 16, and the buyer also loses the expense deduction under Section 43B(h) until payment is made."
    for (const word of demo.split(" ")) {
      handlers.onToken?.(word + " ")
      await new Promise((r) => setTimeout(r, 14))
    }
    handlers.onDone?.(demo, "rag", payload.chat_id || "demo_chat")
  }
}

/* ------------------------------------------------------- knowledge base */

export const ingest = (file: File, userId: string) => {
  const fd = new FormData()
  fd.append("file", file)
  return withFallback(
    () =>
      request<{ file_name: string; chunks_added: number }>(`/api/ingest?user_id=${encodeURIComponent(userId)}`, {
        method: "POST",
        headers: headers(false),
        body: fd,
      }),
    { file_name: file.name, chunks_added: 7 },
  )
}

export const listDocuments = (userId: string) =>
  withFallback(
    () =>
      request<{ document_count: number; documents: Array<{ source: string; chunk_index: number }> }>(
        `/api/documents/${encodeURIComponent(userId)}`,
        { headers: headers() },
      ),
    demoDocuments,
  )

export const deleteDocuments = (userId: string) =>
  withFallback(
    () =>
      request<{ removed_chunks: number }>(`/api/documents/${encodeURIComponent(userId)}`, {
        method: "DELETE",
        headers: headers(),
      }),
    { removed_chunks: demoDocuments.document_count },
  )

export const listMemories = (userId: string) =>
  withFallback(() => request<string[]>(`/api/memories/${encodeURIComponent(userId)}`, { headers: headers() }), demoMemories)

export const addMemory = (user_id: string, content: string) =>
  withFallback(
    () => request<unknown>("/api/memories", { method: "POST", headers: headers(), body: JSON.stringify({ user_id, content }) }),
    { ok: true },
  )

/* ----------------------------------------------------------------- admin */

export const eraseUserData = (userId: string) =>
  withFallback(
    () => request<unknown>(`/api/user/${encodeURIComponent(userId)}/data`, { method: "DELETE", headers: headers() }),
    { ok: true },
  )

export const adminUsers = () =>
  withFallback(async () => {
    const res = await request<any>("/api/admin/users", { headers: headers() })
    return (Array.isArray(res) ? res : res?.users || []) as any[]
  }, [
    { user_id: "dev_user_123", document_count: 13, memory_count: 3 },
    { user_id: "ops_analyst_44", document_count: 5, memory_count: 1 },
  ])

/* ---------------------------------------------------------- organization */

export const createOrg = (name: string) =>
  withFallback(
    () => request<Organization>("/api/org/create", { method: "POST", headers: headers(), body: JSON.stringify({ name }) }),
    { org_id: "demo_org", name, plan: "free", member_count: 1, members: [] },
  )

export const getOrg = () =>
  withFallback(() => request<Organization>("/api/org/me", { headers: headers() }), {
    org_id: "demo_org",
    name: "Acme Components Pvt Ltd",
    plan: "pro",
    member_count: 3,
    members: [
      { email: "founder@acme.in", role: "admin", status: "active" },
      { email: "finance@acme.in", role: "member", status: "active" },
      { email: "counsel@acme.in", role: "viewer", status: "invited" },
    ],
  })

export const getUsage = () => withFallback(() => request<OrgUsage>("/api/org/me/usage", { headers: headers() }), demoUsage)

export const getOrgHistory = (orgId: string) =>
  withFallback(async () => {
    const res = await request<any>(`/api/org/${encodeURIComponent(orgId)}/history`, { headers: headers() })
    return (Array.isArray(res) ? res : res?.analyses || []) as HistoryRow[]
  }, demoHistory)

export const inviteMember = (orgId: string, email: string, role: string) =>
  withFallback(
    () =>
      request<unknown>(`/api/org/${encodeURIComponent(orgId)}/invite`, {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ email, role }),
      }),
    { ok: true },
  )

/* --------------------------------------------------------------- billing */

export const checkout = (plan: string) =>
  withFallback(
    () => request<any>("/api/billing/checkout", { method: "POST", headers: headers(), body: JSON.stringify({ plan }) }),
    {
      order_id: "order_demo_9f81b2",
      amount: plan === "enterprise" ? 499900 : 99900,
      currency: "INR",
      key_id: "rzp_test_sample_key_id",
      plan,
      org_id: "demo_org",
    },
  )

/* ------------------------------------------------------------- api keys */

export const listKeys = () =>
  withFallback(async () => {
    const res = await request<any>("/api/keys", { headers: headers() })
    return (Array.isArray(res) ? res : res?.keys || []) as ApiKey[]
  }, demoKeys)

export const createKey = (name: string) =>
  withFallback(
    () =>
      request<{ key_id: string; name: string; key: string; key_prefix: string; note?: string }>("/api/keys", {
        method: "POST",
        headers: headers(),
        body: JSON.stringify({ name }),
      }),
    {
      key_id: `key_${Date.now()}`,
      name,
      key: `wmb_live_${Math.random().toString(36).slice(2)}${Math.random().toString(36).slice(2)}`,
      key_prefix: "wmb_live",
      note: "Store this secret now. It cannot be retrieved again.",
    },
  )

export const revokeKey = (keyId: string) =>
  withFallback(
    () => request<unknown>(`/api/keys/${encodeURIComponent(keyId)}`, { method: "DELETE", headers: headers() }),
    { ok: true },
  )
