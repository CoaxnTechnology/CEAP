import { useMemo, useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Library, Search, Link2, Trash2, MessageCircle, X, Send, ChevronRight } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import Button from '../../components/ui/Button'
import InsightBanner from '../../components/ui/InsightBanner'
import Modal from '../../components/ui/Modal'
import { api } from '../../lib/api'
import { useApp } from '../../context/AppContext'

export default function KnowledgeHub() {
  const { toast } = useApp()
  const navigate = useNavigate()
  const [cards, setCards] = useState([])
const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
   const [deleteId, setDeleteId] = useState(null)
  const [viewCard, setViewCard] = useState(null)
  const [cardContent, setCardContent] = useState(null)
  const [deptModal, setDeptModal] = useState(null)
  const [chatDepartment, setChatDepartment] = useState(null)
  const [chatMsgs, setChatMsgs] = useState([])
  const [chatInput, setChatInput] = useState('')
  const [chatSending, setChatSending] = useState(false)
  const debounceRef = useRef(null)

  const fetchCards = useCallback(async (searchQ) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (searchQ) params.set('q', searchQ)
      const data = await api(`/api/knowledge/cards?${params}`)
      setCards(Array.isArray(data) ? data : [])
    } catch {
      setCards([])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      fetchCards(q)
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [q, fetchCards])

   async function openCard(doc) {
    setViewCard(doc)
    setCardContent(null)
    try {
      const data = await api(`/api/knowledge/cards/${doc.id}/content`)
      setCardContent(data.text || '')
    } catch {
      setCardContent('')
    }
  }

   async function handleDelete() {
    if (!deleteId) return
    try {
      await api(`/api/knowledge/cards/${deleteId}`, { method: 'DELETE' })
      setDeleteId(null)
      fetchCards()
      toast('Card deleted', 'success')
    } catch {
      toast('Failed to delete', 'error')
    }
  }

  const normDept = (d) => d ? d.charAt(0).toUpperCase() + d.slice(1).toLowerCase() : ''

  const allTypes = useMemo(() => [...new Set(cards.map((c) => c.type))], [cards])

  const grouped = useMemo(() => {
    const groups = {}
    cards.forEach(c => {
      const dept = normDept(c.dept) || (c.source === 'document' ? 'Documents' : 'General')
      if (!groups[dept]) groups[dept] = []
      groups[dept].push({ ...c, dept })
    })
    return Object.entries(groups).sort((a, b) => b[1].length - a[1].length)
  }, [cards])

  const deptDocs = useMemo(() => {
    return grouped.map(([dept, docs]) => [
      dept,
      docs.filter((k) => {
        const matchQ =
          !q ||
          k.title.toLowerCase().includes(q.toLowerCase()) ||
          k.type.toLowerCase().includes(q.toLowerCase())
        return matchQ
      }),
    ]).filter(([, docs]) => docs.length > 0)
  }, [q, grouped])

  const totalDocs = deptDocs.reduce((sum, [, docs]) => sum + docs.length, 0)

  const deptFiles = useMemo(() => {
    if (!deptModal) return []
    const entry = grouped.find(([d]) => d === deptModal)
    return entry ? entry[1] : []
  }, [deptModal, grouped])

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Knowledge Workspace"
        title="Knowledge Hub"
        subtitle="Living institutional knowledge — cards, relationships, summaries. Not a file dump."
         actions={
            <Button variant="secondary" size="sm" onClick={() => navigate('/knowledge/memory')}>
              School Memory
            </Button>
          }
       />

      <InsightBanner
        title="Library AI"
        items={[
          'Fire Safety Certificate is expiring — linked to 2 inspection frameworks',
          'Leadership minutes reference 8 related policies — open graph available',
          'Ask Copilot to summarize any card with citations',
        ]}
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search departments…"
            className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100"
          />
        </div>
        {allTypes.length > 0 && (
          <p className="text-xs text-slate-400">{allTypes.length} types</p>
        )}
      </div>

      <div className="flex items-center justify-between">
         <p className="text-xs text-slate-400">
           {deptDocs.length} departments · {totalDocs} documents
         </p>
       </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
        </div>
      ) : (
        /* Department cards with files inside */
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {deptDocs.map(([dept, docs]) => (
            <Card key={dept} className="card-hover flex flex-col cursor-pointer" onClick={() => setDeptModal(dept)}>
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-navy-50 text-lg font-bold text-navy-700">
                  {dept[0]}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-slate-900">{dept}</h3>
                    <span className="rounded-full bg-navy-50 px-2 py-0.5 text-[11px] font-medium text-navy-600">
                      {docs.length}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 divide-y divide-slate-50">
                {docs.slice(0, 4).map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0 hover:bg-slate-50 rounded-lg cursor-pointer"
                    onClick={(e) => { e.stopPropagation(); openCard(doc) }}
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-50 text-slate-400">
                      <Library className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{doc.title}</p>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400">
                        <span>{doc.type}</span>
                        <span>·</span>
                        <span>{doc.relations} relations</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={doc.status} />
                      <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
                    </div>
                  </div>
                ))}
                {docs.length > 4 && (
                  <p className="py-2 text-center text-[11px] text-slate-400">+{docs.length - 4} more documents</p>
                )}
              </div>

              <div className="mt-3 flex gap-3 border-t border-slate-50 pt-3">
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setChatDepartment(dept); setChatMsgs([]) }}
                  className="inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:text-navy-800"
                >
                  <MessageCircle className="h-3 w-3" /> Ask AI about {dept}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

       {/* Delete confirmation */}
      <Modal
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        title="Delete card?"
        size="sm"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
            <Button variant="danger" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">This will permanently remove this knowledge card. This action cannot be undone.</p>
      </Modal>

      {/* Card detail overlay */}
      {viewCard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setViewCard(null)} />
          <div className="relative z-10 w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-900">{viewCard.title}</h2>
              <button onClick={() => setViewCard(null)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">✕</button>
            </div>
            <div className="flex items-center gap-2 mb-4">
              <StatusBadge status={viewCard.status} />
              <span className="text-xs text-slate-400">{viewCard.type} · {viewCard.dept}</span>
            </div>
            <div className="max-h-[60vh] overflow-y-auto rounded-lg border border-slate-100 bg-slate-50 p-4">
              {cardContent === null ? (
                <div className="flex items-center justify-center py-8">
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
                </div>
              ) : cardContent ? (
                <p className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-700">{cardContent}</p>
              ) : (
                <p className="text-sm text-slate-400">No content available for this item.</p>
              )}
            </div>
            <div className="flex items-center gap-4 mt-4 text-xs text-slate-400">
              <span className="inline-flex items-center gap-1"><Link2 className="h-3 w-3" /> {viewCard.relations} relations</span>
              <span>Updated {viewCard.updated}</span>
            </div>
          </div>
        </div>
      )}

      {/* Department chat panel */}
      {chatDepartment && (
        <div className="fixed bottom-0 right-0 top-0 z-[80] flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl sm:bottom-4 sm:right-4 sm:top-4 sm:rounded-2xl sm:border">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-white">
                <MessageCircle className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">Chat — {chatDepartment}</p>
                <p className="text-[11px] text-slate-400">Ask about {chatDepartment} documents</p>
              </div>
            </div>
            <button type="button" onClick={() => setChatDepartment(null)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {chatMsgs.length === 0 && (
              <div className="flex items-center justify-center h-full">
                <p className="text-sm text-slate-400">Ask a question about {chatDepartment} documents</p>
              </div>
            )}
            {chatMsgs.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'rounded-br-md bg-navy-900 text-white'
                    : 'rounded-bl-md border border-slate-100 bg-slate-50 text-slate-700'
                }`}>
                  {m.text}
                </div>
              </div>
            ))}
            {chatSending && (
              <div className="flex justify-start">
                <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-100 bg-slate-50 px-3.5 py-2.5 text-sm text-slate-400">
                  <div className="flex items-center gap-1">
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '0ms' }} />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '150ms' }} />
                    <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={async (e) => {
              e.preventDefault()
              const q = chatInput.trim()
              if (!q || chatSending) return
              setChatMsgs((m) => [...m, { role: 'user', text: q }])
              setChatInput('')
              setChatSending(true)
              try {
                const data = await api('/api/chat', {
                  method: 'POST',
                  body: JSON.stringify({ question: q, department: chatDepartment }),
                })
                setChatMsgs((m) => [...m, { role: 'assistant', text: data.response || 'No response' }])
              } catch {
                setChatMsgs((m) => [...m, { role: 'assistant', text: 'Failed to get response' }])
              }
              setChatSending(false)
            }}
            className="flex gap-2 border-t border-slate-100 p-3"
          >
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder={`Ask about ${chatDepartment}…`}
              className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white"
            />
            <button
              type="submit"
              disabled={chatSending}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}

      {/* Department modal */}
      {deptModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" onClick={() => setDeptModal(null)} />
          <div className="relative z-10 flex max-h-[85vh] w-full max-w-4xl flex-col rounded-2xl border border-slate-200 bg-white shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-50 text-lg font-bold text-navy-700">
                  {deptModal[0]}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">{deptModal}</h2>
                  <p className="text-xs text-slate-400">{deptFiles.length} documents</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setChatDepartment(deptModal); setChatMsgs([]); setDeptModal(null) }}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-navy-600 hover:bg-navy-50"
                >
                  <MessageCircle className="h-3.5 w-3.5" /> Ask AI
                </button>
                <button onClick={() => setDeptModal(null)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid gap-4 sm:grid-cols-2">
                {deptFiles.map((doc) => (
                  <Card
                    key={doc.id}
                    className="flex flex-col cursor-pointer"
                    onClick={() => setViewCard(doc)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy-50 text-navy-600">
                        <Library className="h-4 w-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                            {doc.type}
                          </span>
                          <StatusBadge status={doc.status} />
                        </div>
                        <h3 className="mt-1 truncate text-sm font-semibold text-slate-900">{doc.title}</h3>
                      </div>
                    </div>
                    {doc.summary && (
                      <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-500">{doc.summary}</p>
                    )}
                    <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Link2 className="h-3 w-3" /> {doc.relations} relations
                      </span>
                      <span>Updated {doc.updated}</span>
                    </div>
                  </Card>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}