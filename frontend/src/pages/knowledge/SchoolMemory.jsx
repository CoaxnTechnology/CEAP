import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, Search, ArrowLeft, RefreshCw } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Section from '../../components/ui/Section'
import Button from '../../components/ui/Button'
import { api } from '../../lib/api'
import { useApp } from '../../context/AppContext'

const kindColor = {
  Decision: 'bg-violet-500',
  Meeting: 'bg-navy-600',
  Approval: 'bg-emerald-500',
  Policy: 'bg-amber-500',
  Discussion: 'bg-sky-500',
  Document: 'bg-slate-500',
}

export default function SchoolMemory() {
  const navigate = useNavigate()
  const { toast } = useApp()
  const [q, setQ] = useState('')
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchMemories = () => {
    setLoading(true)
    api('/api/knowledge/memory')
      .then((data) => setMemories(data || []))
      .catch(() => setMemories([]))
      .finally(() => setLoading(false))
  }

  const reindex = () => {
    fetchMemories()
    toast('Memory re-indexed', 'success')
  }

  useEffect(() => fetchMemories(), [])

  const filtered = useMemo(() => {
    if (!q) return memories
    const lq = q.toLowerCase()
    return memories.filter(
      (m) =>
        m.title.toLowerCase().includes(lq) ||
        m.kind.toLowerCase().includes(lq) ||
        m.tags.some((t) => t.toLowerCase().includes(lq))
    )
  }, [memories, q])

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <button
        type="button"
        onClick={() => navigate('/knowledge')}
        className="inline-flex items-center gap-1 text-xs font-medium text-navy-600"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Knowledge Hub
      </button>

      <PageHeader
        eyebrow="Institutional Memory"
        title="School Memory"
        subtitle="Every meeting, decision, policy, discussion, and approval — searchable forever."
        actions={
          <Button size="sm" variant="secondary" onClick={reindex}>
            <RefreshCw className="h-3.5 w-3.5" /> Re-index
          </Button>
        }
      />

      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search decisions, meetings, approvals…"
          className="field !pl-10"
        />
      </div>

      <Section title="Memory stream" padding={false}>
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
            <RefreshCw className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {filtered.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  onClick={() => toast(`Memory: ${m.title}`, 'info')}
                  className="flex w-full gap-4 px-5 py-4 text-left hover:bg-slate-50/80"
                >
                  <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${kindColor[m.kind] || 'bg-navy-500'}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-500">
                        {m.kind}
                      </span>
                      <span className="text-[11px] text-slate-400">{m.when}</span>
                    </div>
                    <p className="mt-1 text-sm font-semibold text-slate-900">{m.title}</p>
                    <p className="text-xs text-slate-500">
                      {m.actor} · {m.tags.join(' · ')}
                    </p>
                  </div>
                </button>
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-5 py-8 text-center text-sm text-slate-500">
                {q ? 'No memories match your search.' : 'No memories yet. Start using the system to build your school memory.'}
              </li>
            )}
          </ul>
        )}
      </Section>
    </div>
  )
}
