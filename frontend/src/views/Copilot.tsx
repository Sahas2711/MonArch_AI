import React, { useEffect, useMemo, useRef, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Field, Modal, Spinner } from "../components/ui"
import { chat, streamChat } from "../lib/api"
import { copyText, download, pct, titleCase } from "../lib/format"
import {
  composePrompt,
  getChatPrefs,
  loadConversations,
  saveChatPrefs,
  saveConversations,
  titleFrom,
  type ChatPrefs,
  type Conversation,
  type StoredMessage,
} from "../lib/prefs"

const PROMPT_PACKS: Array<{ group: string; items: string[] }> = [
  {
    group: "Get paid",
    items: [
      "An invoice is 70 days overdue. What exactly can I claim and under which section?",
      "Draft a firm but professional payment reminder that mentions statutory interest.",
      "The buyer says their process is 90 days. How do I answer that in one paragraph?",
    ],
  },
  {
    group: "Before signing",
    items: [
      "What is the longest payment period I can legally accept as a micro enterprise?",
      "Rewrite a 120 day payment clause so it is compliant but still commercially acceptable.",
      "Which clauses in a purchase order usually void my MSME protection?",
    ],
  },
  {
    group: "Escalate",
    items: [
      "Walk me through filing on MSME Samadhaan, step by step, with what I need ready.",
      "Does an arbitration clause stop me from using the Facilitation Council?",
      "How do I use Section 43B(h) as leverage without threatening the relationship?",
    ],
  },
]

let seq = 0
const uid = () => `m${Date.now().toString(36)}${seq++}`
const words = (s: string) => (s.trim() ? s.trim().split(/\s+/).length : 0)

export const Copilot: React.FC = () => {
  const { userId, toast, go } = useApp()

  const [prefs, setPrefs] = useState<ChatPrefs>(getChatPrefs())
  const [convos, setConvos] = useState<Conversation[]>(loadConversations())
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<StoredMessage[]>([])
  const [chatId, setChatId] = useState<string | undefined>()

  const [input, setInput] = useState("")
  const [busy, setBusy] = useState(false)
  const [route, setRoute] = useState<string | undefined>()
  const [context, setContext] = useState<string | undefined>()
  const [scores, setScores] = useState<Record<string, unknown> | undefined>()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [sideTab, setSideTab] = useState<"context" | "prompts" | "quality">("prompts")

  const abort = useRef<AbortController | null>(null)
  const endRef = useRef<HTMLDivElement | null>(null)
  const boxRef = useRef<HTMLTextAreaElement | null>(null)

  /* ------------------------------------------------------------ persistence */

  const persist = (next: Conversation[]) => {
    setConvos(next)
    saveConversations(next)
  }

  const upsertConversation = (msgs: StoredMessage[], newChatId?: string) => {
    const id = activeId || uid()
    const firstUser = msgs.find((m) => m.role === "user")
    const existing = convos.find((c) => c.id === id)
    const convo: Conversation = {
      id,
      chatId: newChatId || chatId || existing?.chatId,
      title: existing?.title && !prefs.autoTitle ? existing.title : titleFrom(firstUser?.content || ""),
      pinned: existing?.pinned,
      createdAt: existing?.createdAt || Date.now(),
      updatedAt: Date.now(),
      messages: msgs,
    }
    if (!activeId) setActiveId(id)
    persist([convo, ...convos.filter((c) => c.id !== id)])
  }

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "j") {
        e.preventDefault()
        newChat()
      }
      if ((e.metaKey || e.ctrlKey) && e.key === ",") {
        e.preventDefault()
        setSettingsOpen(true)
      }
      if (e.key === "Escape" && busy) stop()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [busy])

  const updatePrefs = (patch: Partial<ChatPrefs>) => {
    const merged = { ...prefs, ...patch }
    setPrefs(merged)
    saveChatPrefs(merged)
  }

  /* ------------------------------------------------------------- messaging */

  const newChat = () => {
    abort.current?.abort()
    setActiveId(null)
    setMessages([])
    setChatId(undefined)
    setContext(undefined)
    setScores(undefined)
    setRoute(undefined)
    setBusy(false)
    setTimeout(() => boxRef.current?.focus(), 30)
  }

  const openConversation = (c: Conversation) => {
    abort.current?.abort()
    setActiveId(c.id)
    setMessages(c.messages)
    setChatId(c.chatId)
    setBusy(false)
    setContext(undefined)
    setScores(undefined)
  }

  const send = async (text: string, replaceLast = false) => {
    const q = text.trim()
    if (!q || busy) return

    setInput("")
    setContext(undefined)
    setScores(undefined)

    const base = replaceLast ? messages.slice(0, -1) : messages
    const userMsg: StoredMessage = { id: uid(), role: "user", content: q, at: Date.now() }
    const replyId = uid()
    const withUser = replaceLast ? base : [...base, userMsg]
    const pending: StoredMessage[] = [...withUser, { id: replyId, role: "assistant", content: "", at: Date.now() }]
    setMessages(pending)
    setBusy(true)

    const payload = {
      user_inp: composePrompt(prefs, q),
      user_id: userId,
      chat_id: chatId,
      eval_response: prefs.evaluate,
    }

    const finish = (content: string, meta: { chat_id?: string; context?: string; eval_scores?: any; route?: string }) => {
      const done = pending.map((m) => (m.id === replyId ? { ...m, content, route: meta.route } : m))
      setMessages(done)
      if (meta.chat_id) setChatId(meta.chat_id)
      if (meta.context) setContext(meta.context)
      if (meta.eval_scores) setScores(meta.eval_scores)
      upsertConversation(done, meta.chat_id)
      setBusy(false)
    }

    if (!prefs.stream) {
      try {
        const res = await chat(payload)
        setRoute(res.route)
        finish(res.output, { chat_id: res.chat_id, context: res.context, eval_scores: res.eval_scores, route: res.route })
      } catch (err: any) {
        finish(`The assistant could not answer: ${err?.message || err}`, {})
      }
      return
    }

    const ctrl = new AbortController()
    abort.current = ctrl
    let acc = ""
    let seenRoute: string | undefined

    await streamChat(
      payload,
      {
        onRoute: (r) => {
          seenRoute = r
          setRoute(r)
          setMessages((m) => m.map((x) => (x.id === replyId ? { ...x, route: r } : x)))
        },
        onToken: (t) => {
          acc += t
          setMessages((m) => m.map((x) => (x.id === replyId ? { ...x, content: acc } : x)))
        },
        onDone: (p: any) => {
          finish(acc || p?.output || "", {
            chat_id: p?.chat_id,
            context: p?.context,
            eval_scores: p?.eval_scores,
            route: seenRoute,
          })
        },
        onError: (e) => finish(acc || `The assistant could not answer: ${e}`, { route: seenRoute }),
      },
      ctrl.signal,
    )
  }

  const stop = () => {
    abort.current?.abort()
    setBusy(false)
    upsertConversation(messages)
  }

  const regenerate = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === "user")
    if (!lastUser) return
    setMessages(messages.slice(0, messages.length - 1))
    send(lastUser.content, true)
  }

  const react = (id: string, liked: "up" | "down") => {
    const next = messages.map((m) => (m.id === id ? { ...m, liked: m.liked === liked ? undefined : liked } : m))
    setMessages(next)
    upsertConversation(next)
    toast(liked === "up" ? "Marked as useful" : "Marked for review", "success")
  }

  const transcript = useMemo(
    () => messages.map((m) => `### ${m.role === "user" ? "You" : "Copilot"}\n\n${m.content}`).join("\n\n"),
    [messages],
  )

  const filteredConvos = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return convos
    return convos.filter(
      (c) => c.title.toLowerCase().includes(needle) || c.messages.some((m) => m.content.toLowerCase().includes(needle)),
    )
  }, [convos, search])

  /* ------------------------------------------------------------------ view */

  return (
    <div className="cp">
      {/* conversation rail */}
      <aside className="cp-rail">
        <Button variant="primary" size="sm" block onClick={newChat}>New conversation</Button>
        <input className="input search" placeholder="Search conversations" value={search} onChange={(e) => setSearch(e.target.value)} />

        <div className="cp-list">
          {filteredConvos.length === 0 ? (
            <p className="card-sub" style={{ padding: "8px 4px" }}>Nothing saved yet. Conversations appear here as you use the copilot.</p>
          ) : (
            filteredConvos.map((c) => (
              <div key={c.id} className={`cp-item ${activeId === c.id ? "on" : ""}`}>
                <button className="cp-open" onClick={() => openConversation(c)}>
                  <b>{c.pinned ? "\u2605 " : ""}{c.title}</b>
                  <span>{new Date(c.updatedAt).toLocaleDateString()} · {c.messages.length} messages</span>
                </button>
                <div className="cp-item-tools">
                  <button
                    title="Pin"
                    onClick={() => persist(convos.map((x) => (x.id === c.id ? { ...x, pinned: !x.pinned } : x)))}
                  >
                    {c.pinned ? "\u2605" : "\u2606"}
                  </button>
                  <button
                    title="Delete"
                    onClick={() => {
                      persist(convos.filter((x) => x.id !== c.id))
                      if (activeId === c.id) newChat()
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="cp-rail-foot">
          <Button size="sm" variant="ghost" block onClick={() => setSettingsOpen(true)}>Copilot settings</Button>
          <Button size="sm" variant="ghost" block onClick={() => go("knowledge")}>Manage knowledge</Button>
        </div>
      </aside>

      {/* conversation */}
      <section className="cp-main">
        <header className="cp-top">
          <div>
            <b>MSME copilot</b>
            <div className="card-sub">
              {titleCase(prefs.persona)} · {titleCase(prefs.verbosity)} · {prefs.stream ? "streaming" : "single response"}
            </div>
          </div>
          <div className="spacer" />
          {route && <Badge tone="purple">route: {titleCase(route)}</Badge>}
          {busy ? (
            <Button size="sm" variant="danger" onClick={stop}>Stop</Button>
          ) : (
            <>
              {messages.length > 0 && <Button size="sm" onClick={regenerate}>Regenerate</Button>}
              {messages.length > 0 && (
                <Button size="sm" onClick={() => download("copilot-conversation.md", transcript, "text/markdown")}>Export</Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => setSettingsOpen(true)}>Settings</Button>
            </>
          )}
        </header>

        <div className="cp-scroll">
          {messages.length === 0 ? (
            <div className="cp-intro">
              <h2>What are you trying to get paid for?</h2>
              <p className="card-sub">
                Ask in plain English. Every answer names the statute or the document it came from, and you can see the
                retrieved passages on the right.
              </p>
              {PROMPT_PACKS.map((pack) => (
                <div key={pack.group} className="cp-pack">
                  <span className="cp-pack-label">{pack.group}</span>
                  <div className="suggest">
                    {pack.items.map((s) => (
                      <button key={s} onClick={() => send(s)}>{s}</button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            messages.map((m) => (
              <div key={m.id} className={`bubble-row ${m.role}`}>
                <div className={`bubble ${m.role}`}>
                  {m.content || (busy ? <Spinner size={14} /> : "")}
                  {busy && m.role === "assistant" && m.content && m.id === messages[messages.length - 1].id ? (
                    <span className="caret" />
                  ) : null}
                </div>
                {m.role === "assistant" && m.content && (
                  <div className="bubble-tools">
                    <button onClick={async () => toast((await copyText(m.content)) ? "Answer copied" : "Copy blocked", "success")}>Copy</button>
                    <button className={m.liked === "up" ? "on" : ""} onClick={() => react(m.id, "up")}>Useful</button>
                    <button className={m.liked === "down" ? "on" : ""} onClick={() => react(m.id, "down")}>Needs work</button>
                    {m.route && <span className="bubble-route">{m.route}</span>}
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={endRef} />
        </div>

        <form
          className="cp-input"
          onSubmit={(e) => {
            e.preventDefault()
            send(input)
          }}
        >
          <textarea
            ref={boxRef}
            className="textarea"
            rows={2}
            placeholder="Ask about payment terms, interest, Samadhaan filing, or paste a clause you were sent"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                send(input)
              }
            }}
          />
          <div className="cp-input-side">
            <Button variant="primary" loading={busy} disabled={!input.trim()}>Send</Button>
            <span className="cp-count">{words(input)} words</span>
          </div>
        </form>
      </section>

      {/* inspector */}
      <aside className="cp-side">
        <div className="seg" style={{ marginBottom: 12 }}>
          <button className={sideTab === "prompts" ? "on" : ""} onClick={() => setSideTab("prompts")}>Guides</button>
          <button className={sideTab === "context" ? "on" : ""} onClick={() => setSideTab("context")}>Sources</button>
          <button className={sideTab === "quality" ? "on" : ""} onClick={() => setSideTab("quality")}>Quality</button>
        </div>

        {sideTab === "context" && (
          <Card soft>
            <CardHead title="Retrieved context" sub="What grounded the last answer" />
            {context ? (
              <div className="pre" style={{ maxHeight: 340, overflow: "auto", whiteSpace: "pre-wrap" }}>{context}</div>
            ) : (
              <p className="card-sub">Ask something and the retrieved passages appear here.</p>
            )}
          </Card>
        )}

        {sideTab === "quality" && (
          <Card soft>
            <CardHead title="Answer quality" sub="Evaluation harness scores" />
            {scores ? (
              <div className="stack-sm">
                {Object.entries(scores).map(([k, v]) => (
                  <div className="meter-row" key={k}>
                    <div className="meter-top"><span>{titleCase(k)}</span><b>{typeof v === "number" ? pct(v) : String(v)}</b></div>
                    {typeof v === "number" && (
                      <div className={`meter ${v >= 0.8 ? "green" : v >= 0.5 ? "orange" : "red"}`}>
                        <span style={{ width: `${Math.min(100, v * 100)}%` }} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="card-sub">
                {prefs.evaluate
                  ? "Scores arrive with the next answer."
                  : "Evaluation is switched off in settings."}
              </p>
            )}
          </Card>
        )}

        {sideTab === "prompts" && (
          <>
            <Card soft>
              <CardHead title="How to get a useful answer" sub="Three habits that work" />
              <ul className="check-list">
                <li>Give the number: invoice value and how many days overdue.</li>
                <li>Paste the actual clause instead of describing it.</li>
                <li>Say what you want out loud: a reminder, a rewrite, or a filing plan.</li>
              </ul>
            </Card>
            <Card soft>
              <CardHead title="Shortcuts" />
              <div className="stack-sm">
                <div className="kv"><span>Send</span><span><span className="kbd">Enter</span></span></div>
                <div className="kv"><span>New line</span><span><span className="kbd">Shift</span> <span className="kbd">Enter</span></span></div>
                <div className="kv"><span>New conversation</span><span><span className="kbd">⌘</span> <span className="kbd">J</span></span></div>
                <div className="kv"><span>Settings</span><span><span className="kbd">⌘</span> <span className="kbd">,</span></span></div>
                <div className="kv"><span>Stop generating</span><span><span className="kbd">Esc</span></span></div>
              </div>
            </Card>
          </>
        )}
      </aside>

      {/* settings */}
      <Modal
        open={settingsOpen}
        title="Copilot settings"
        onClose={() => setSettingsOpen(false)}
        wide
        footer={<Button variant="primary" onClick={() => setSettingsOpen(false)}>Done</Button>}
      >
        <div className="grid g2">
          <div className="stack">
            <Field label="Persona" hint="the voice it answers in">
              <select className="select" value={prefs.persona} onChange={(e) => updatePrefs({ persona: e.target.value as ChatPrefs["persona"] })}>
                <option value="advisor">Compliance advisor</option>
                <option value="negotiator">Hard negotiator</option>
                <option value="counsel">Cautious counsel</option>
                <option value="plain">Plain English explainer</option>
              </select>
            </Field>

            <Field label="Answer length">
              <div className="seg">
                {(["concise", "balanced", "thorough"] as const).map((v) => (
                  <button key={v} type="button" className={prefs.verbosity === v ? "on" : ""} onClick={() => updatePrefs({ verbosity: v })}>
                    {titleCase(v)}
                  </button>
                ))}
              </div>
            </Field>

            <Field label={`Creativity ${prefs.temperature.toFixed(1)}`} hint="lower stays closer to the statute">
              <input type="range" min={0} max={1} step={0.1} value={prefs.temperature} onChange={(e) => updatePrefs({ temperature: Number(e.target.value) })} />
            </Field>

            <Field label="Standing instruction" hint="sent with every question">
              <textarea
                className="textarea"
                rows={4}
                value={prefs.systemPrompt}
                onChange={(e) => updatePrefs({ systemPrompt: e.target.value })}
                placeholder="We are a micro enterprise in Coimbatore supplying auto components. Always quote the section."
              />
            </Field>
          </div>

          <div className="stack-sm">
            {([
              ["stream", "Stream the answer as it is written"],
              ["citations", "Ask for the source of every claim"],
              ["useMemories", "Use my saved memories"],
              ["evaluate", "Score answer quality"],
              ["autoTitle", "Name conversations automatically"],
            ] as Array<[keyof ChatPrefs, string]>).map(([key, label]) => (
              <label className="switch-row" key={key as string}>
                <input type="checkbox" checked={Boolean(prefs[key])} onChange={(e) => updatePrefs({ [key]: e.target.checked } as Partial<ChatPrefs>)} />
                <span>{label}</span>
              </label>
            ))}

            <div className="callout" style={{ marginTop: 10 }}>
              Preferences are stored on this device and shape the instruction block sent with each question. The routing
              decision itself stays with the backend agent graph.
            </div>

            <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
              <Button size="sm" variant="ghost" onClick={() => { const f = getChatPrefs(true); setPrefs(f); saveChatPrefs(f) }}>Reset defaults</Button>
              <Button size="sm" variant="danger" onClick={() => { persist([]); newChat(); toast("All saved conversations cleared", "success") }}>Clear history</Button>
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
