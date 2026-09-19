import React, { useEffect, useMemo, useState } from "react"
import { useApp } from "../store/app"
import { Badge, Button, Card, CardHead, Dropzone, Empty, Field, Modal, SkeletonRows } from "../components/ui"
import { addMemory, deleteDocuments, ingest, listDocuments, listMemories } from "../lib/api"
import { num } from "../lib/format"

export const Knowledge: React.FC = () => {
  const { userId, toast } = useApp()
  const [docs, setDocs] = useState<{ document_count: number; documents: Array<{ source: string; chunk_index: number }> } | null>(null)
  const [memories, setMemories] = useState<string[] | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [q, setQ] = useState("")
  const [busy, setBusy] = useState(false)
  const [memo, setMemo] = useState("")
  const [wipeOpen, setWipeOpen] = useState(false)
  const [confirmText, setConfirmText] = useState("")

  const load = async () => {
    const [d, m] = await Promise.all([listDocuments(userId), listMemories(userId)])
    setDocs(d)
    setMemories(m)
  }

  useEffect(() => {
    load()
  }, [userId])

  const grouped = useMemo(() => {
    const map = new Map<string, number>()
    ;(docs?.documents || []).forEach((d) => map.set(d.source, (map.get(d.source) || 0) + 1))
    const list = [...map.entries()].map(([source, chunks]) => ({ source, chunks }))
    const needle = q.trim().toLowerCase()
    return (needle ? list.filter((l) => l.source.toLowerCase().includes(needle)) : list).sort((a, b) => b.chunks - a.chunks)
  }, [docs, q])

  const upload = async () => {
    if (!file) return
    setBusy(true)
    const res = await ingest(file, userId)
    setBusy(false)
    setFile(null)
    toast(`${res.file_name} indexed into ${num(res.chunks_added)} chunks`, "success")
    load()
  }

  const saveMemory = async (e: React.FormEvent) => {
    e.preventDefault()
    if (memo.trim().length < 4) return
    await addMemory(userId, memo.trim())
    setMemo("")
    toast("Memory saved for the copilot", "success")
    load()
  }

  const wipe = async () => {
    const res = await deleteDocuments(userId)
    setWipeOpen(false)
    setConfirmText("")
    toast(`Removed ${num(res.removed_chunks)} chunks`, "success")
    load()
  }

  const maxChunks = Math.max(1, ...grouped.map((g) => g.chunks))

  return (
    <>
      <div className="page-head">
        <div className="page-hero-row">
          <div>
            <p className="eyebrow">Retrieval index</p>
            <h1>Knowledge base</h1>
            <p>
              Everything the copilot can cite: your uploaded contracts and policies, plus the standing instructions it
              remembers between sessions.
            </p>
          </div>
          <div className="spacer" />
          <div className="row" style={{ gap: 8 }}>
            <Badge tone="blue">{num(docs?.document_count)} chunks</Badge>
            <Button size="sm" onClick={load}>Refresh</Button>
          </div>
        </div>
      </div>

      <div className="grid g3">
        <div className="stack g2">
          <Card>
            <CardHead title="Add a document" sub="PDF, DOCX or TXT. Chunked and embedded for retrieval." />
            <Dropzone file={file} onFile={setFile} />
            <div className="row" style={{ gap: 8, marginTop: 12 }}>
              <Button variant="primary" loading={busy} disabled={!file} onClick={upload}>Index this file</Button>
              {file && <Button variant="ghost" onClick={() => setFile(null)}>Remove</Button>}
            </div>
          </Card>

          <Card>
            <CardHead
              title="Indexed sources"
              sub="Grouped by file, with chunk counts"
              right={<span className="count-pill">{grouped.length} files</span>}
            />
            <div className="toolbar" style={{ marginBottom: 12 }}>
              <input className="input search" placeholder="Filter by file name" value={q} onChange={(e) => setQ(e.target.value)} />
              <Button size="sm" variant="danger" disabled={!docs?.document_count} onClick={() => setWipeOpen(true)}>Delete all</Button>
            </div>
            {docs === null ? (
              <SkeletonRows rows={4} height={24} />
            ) : grouped.length === 0 ? (
              <Empty icon="\u25e7" title="Nothing indexed yet" hint="Upload a contract or policy pack and the copilot will cite it." />
            ) : (
              <div className="stack-sm">
                {grouped.map((g) => (
                  <div className="meter-row" key={g.source}>
                    <div className="meter-top">
                      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{g.source}</span>
                      <b>{g.chunks} chunks</b>
                    </div>
                    <div className="meter"><span style={{ width: `${(g.chunks / maxChunks) * 100}%` }} /></div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        <div className="stack">
          <Card>
            <CardHead title="Copilot memories" sub="Facts it carries into every conversation" />
            <form className="stack-sm" onSubmit={saveMemory}>
              <Field label="New memory" hint="for example: we are a registered micro enterprise in Tamil Nadu">
                <textarea className="textarea" rows={3} value={memo} onChange={(e) => setMemo(e.target.value)} />
              </Field>
              <Button variant="primary" size="sm" block disabled={memo.trim().length < 4}>Save memory</Button>
            </form>
            <div className="stack-sm" style={{ marginTop: 14 }}>
              {memories === null ? (
                <SkeletonRows rows={3} height={20} />
              ) : memories.length === 0 ? (
                <p className="card-sub">No memories stored yet.</p>
              ) : (
                memories.map((m, i) => (
                  <div className="mini" key={i}>
                    <div className="k">Memory {i + 1}</div>
                    <div style={{ fontSize: 13, marginTop: 4, lineHeight: 1.55 }}>{m}</div>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card soft>
            <CardHead title="How retrieval is used" sub="Grounded answers only" />
            <ul className="check-list">
              <li>Copilot answers cite the retrieved chunk, so you can check the source.</li>
              <li>Audits match clauses against statute passages, not model memory.</li>
              <li>Deleting a source removes its chunks from future answers immediately.</li>
            </ul>
          </Card>
        </div>
      </div>

      <Modal
        open={wipeOpen}
        title="Delete every indexed chunk"
        onClose={() => setWipeOpen(false)}
        footer={
          <>
            <Button onClick={() => setWipeOpen(false)}>Cancel</Button>
            <Button variant="danger" disabled={confirmText !== "DELETE"} onClick={wipe}>Delete permanently</Button>
          </>
        }
      >
        <div className="stack">
          <div className="callout warn">
            This removes {num(docs?.document_count)} chunks for <span className="mono">{userId}</span>. Answers will stop
            citing these documents. It cannot be undone.
          </div>
          <Field label="Type DELETE to confirm">
            <input className="input mono" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder="DELETE" />
          </Field>
        </div>
      </Modal>
    </>
  )
}
