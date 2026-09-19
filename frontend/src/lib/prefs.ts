/**
 * Copilot preferences and stored conversations.
 *
 * Preferences are per device (localStorage) and are applied to every request
 * the chat screen makes. Conversations are stored locally so the sidebar keeps
 * working even when the backend is only holding chat_id state.
 */

export type ChatPrefs = {
  persona: "advisor" | "negotiator" | "counsel" | "plain"
  verbosity: "concise" | "balanced" | "thorough"
  temperature: number
  stream: boolean
  citations: boolean
  useMemories: boolean
  evaluate: boolean
  autoTitle: boolean
  systemPrompt: string
}

export const DEFAULT_PREFS: ChatPrefs = {
  persona: "advisor",
  verbosity: "balanced",
  temperature: 0.2,
  stream: true,
  citations: true,
  useMemories: true,
  evaluate: true,
  autoTitle: true,
  systemPrompt: "",
}

const PREFS_KEY = "monarch.chat.prefs"
const CONVOS_KEY = "monarch.chat.conversations"
const ls = typeof localStorage !== "undefined" ? localStorage : null

export function getChatPrefs(fresh = false): ChatPrefs {
  if (fresh) return { ...DEFAULT_PREFS }
  try {
    const raw = ls?.getItem(PREFS_KEY) || ls?.getItem("wemboo.chat.prefs")
    return raw ? { ...DEFAULT_PREFS, ...(JSON.parse(raw) as ChatPrefs) } : { ...DEFAULT_PREFS }
  } catch {
    return { ...DEFAULT_PREFS }
  }
}

export function saveChatPrefs(prefs: ChatPrefs) {
  ls?.setItem(PREFS_KEY, JSON.stringify(prefs))
}

export const PERSONA_PROMPT: Record<ChatPrefs["persona"], string> = {
  advisor: "Answer as an MSME payment compliance advisor. Cite the exact section of the MSMED Act or Income Tax Act you rely on.",
  negotiator: "Answer as a firm commercial negotiator. Give wording I can send to the buyer today, with the leverage stated plainly.",
  counsel: "Answer as cautious in-house counsel. Flag assumptions, risks and where a lawyer must review before I act.",
  plain: "Explain in plain English with no legal jargon, as if I have never read the Act, then give the one action to take next.",
}

export const VERBOSITY_PROMPT: Record<ChatPrefs["verbosity"], string> = {
  concise: "Keep the answer under 120 words.",
  balanced: "Keep the answer focused, roughly 150 to 250 words.",
  thorough: "Give a complete answer with the reasoning, the statute references and the next steps.",
}

/** Builds the instruction block sent ahead of the user's question. */
export function composePrompt(prefs: ChatPrefs, question: string): string {
  const parts = [
    PERSONA_PROMPT[prefs.persona],
    VERBOSITY_PROMPT[prefs.verbosity],
    prefs.citations ? "Name the source document or statute for each claim." : "",
    prefs.useMemories ? "" : "Ignore stored memories for this answer.",
    prefs.systemPrompt.trim(),
  ].filter(Boolean)
  return `${parts.join(" ")}\n\nQuestion: ${question}`
}

/* ----------------------------------------------------------- conversations */

export type StoredMessage = {
  id: string
  role: "user" | "assistant"
  content: string
  route?: string
  at: number
  liked?: "up" | "down"
}

export type Conversation = {
  id: string
  chatId?: string
  title: string
  pinned?: boolean
  createdAt: number
  updatedAt: number
  messages: StoredMessage[]
}

export function loadConversations(): Conversation[] {
  try {
    const raw = ls?.getItem(CONVOS_KEY)
    const list = raw ? (JSON.parse(raw) as Conversation[]) : []
    return list.sort((a, b) => Number(b.pinned || 0) - Number(a.pinned || 0) || b.updatedAt - a.updatedAt)
  } catch {
    return []
  }
}

export function saveConversations(list: Conversation[]) {
  ls?.setItem(CONVOS_KEY, JSON.stringify(list.slice(0, 60)))
}

export function titleFrom(question: string): string {
  const clean = question.replace(/\s+/g, " ").trim()
  return clean.length > 48 ? clean.slice(0, 46) + "\u2026" : clean || "New conversation"
}
