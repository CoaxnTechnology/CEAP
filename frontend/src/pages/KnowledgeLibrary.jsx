import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Library, Search, MessageSquare, FilePenLine, ChevronRight } from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

export default function KnowledgeLibrary() {
  const navigate = useNavigate()
  const { toast } = useApp()
  const [query, setQuery] = useState('')
  const [type, setType] = useState('All')
  const [deptFilter, setDeptFilter] = useState('All')
  const [docs, setDocs] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(true)

  const fetchDocs = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ status: 'active' })
      if (query) params.set('search', query)
      const [docData, deptData] = await Promise.all([
        api(`/api/repository/documents?${params}`),
        api('/api/repository/departments'),
      ])
      setDocs((docData.documents || []).map(d => ({
        id: d.id,
        title: d.name,
        department: d.department_name || d.department_id || '',
        status: d.status === 'active' ? 'Current' : d.status,
        year: d.created_at ? new Date(d.created_at * 1000).getFullYear().toString() : '',
        updated: d.updated_at ? new Date(d.updated_at * 1000).toISOString().slice(0, 10) : '',
        owner: d.owner_email || '',
        description: d.description || '',
      })))
      setDepartments(deptData.departments || [])
    } catch {
      setDocs([])
    }
    setLoading(false)
  }, [query])

  useEffect(() => { fetchDocs() }, [fetchDocs])

  const types = useMemo(
    () => ['All', ...new Set(docs.map((k) => k.type || 'Document'))],
    [docs]
  )

  const deptDocs = useMemo(() => {
    const groups = {}
    docs.forEach((k) => {
      const d = k.department || 'Other'
      if (!groups[d]) groups[d] = []
      groups[d].push(k)
    })
    return Object.entries(groups).sort((a, b) => b[1].length - a[1].length)
  }, [docs])

  const filtered = useMemo(() => {
    return deptDocs
      .map(([dept, list]) => [
        dept,
        list.filter((k) => {
          const matchQ =
            !query ||
            k.title.toLowerCase().includes(query.toLowerCase())
          const matchT = type === 'All' || k.type === type
          const matchD = deptFilter === 'All' || k.department === deptFilter
          return matchQ && matchT && matchD
        }),
      ])
      .filter(([, list]) => list.length > 0)
  }, [query, type, deptFilter, deptDocs])

  const totalDocs = filtered.reduce((sum, [, list]) => sum + list.length, 0)

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Knowledge Library</h1>
          <p className="mt-1 text-sm text-slate-500">
            Browse the institutional knowledge base — policies, SOPs, certificates and more
          </p>
        </div>
        <Button size="sm" onClick={() => navigate('/generate')}>
          <FilePenLine className="h-4 w-4" /> Generate document
        </Button>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter documents…"
            className="w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100"
          />
        </div>
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-navy-400 sm:w-40"
        >
          <option value="All">All departments</option>
          {departments.map((d) => (
            <option key={d.id} value={d.name}>{d.name}</option>
          ))}
        </select>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm outline-none focus:border-navy-400 sm:w-40"
        >
          {types.map((t) => (
            <option key={t} value={t}>
              {t === 'All' ? 'All types' : t}
            </option>
          ))}
        </select>
      </div>

      <p className="text-sm text-slate-500">
        <span className="font-semibold text-slate-700">{filtered.length}</span> departments
        {' · '}
        <span className="font-semibold text-slate-700">{totalDocs}</span> documents
      </p>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
        </div>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {filtered.map(([dept, list]) => (
            <Card key={dept} className="flex flex-col">
              <div className="flex items-start gap-3">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-navy-50 text-lg font-bold text-navy-700">
                  {dept[0]}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-slate-900">{dept}</h3>
                    <span className="rounded-full bg-navy-50 px-2 py-0.5 text-[11px] font-medium text-navy-600">
                      {list.length}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-4 divide-y divide-slate-50">
                {list.map((doc) => (
                  <div
                    key={doc.id}
                    onClick={() => navigate(`/library/${doc.id}`, { state: { doc } })}
                    className="flex cursor-pointer items-center gap-3 py-2.5 first:pt-0 last:pb-0 hover:opacity-80"
                  >
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-50 text-slate-400">
                      <Library className="h-4 w-4" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-900">{doc.title}</p>
                      <div className="flex items-center gap-2 text-[11px] text-slate-400">
                        <span>{doc.type || 'Document'}</span>
                        <span>·</span>
                        <span>{doc.year}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={doc.status} />
                      <ChevronRight className="h-3.5 w-3.5 text-slate-300" />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-3 flex gap-3 border-t border-slate-50 pt-3">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate('/chat', {
                      state: { seedQuestion: `Summarize ${dept} department policies for staff` },
                    })
                  }}
                  className="inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:underline"
                >
                  <MessageSquare className="h-3 w-3" /> Ask AI about {dept}
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <Card className="py-12 text-center">
          <Library className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 text-sm text-slate-500">No documents match your filters</p>
          <Button
            className="mt-4"
            variant="secondary"
            onClick={() => {
              setQuery('')
              setType('All')
              setDeptFilter('All')
              toast('Filters reset', 'info')
            }}
          >
            Reset filters
          </Button>
        </Card>
      )}
    </div>
  )
}
