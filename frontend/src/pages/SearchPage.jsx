import { useState, useMemo, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import {
  Search,
  Filter,
  ExternalLink,
  MessageSquare,
  BookOpen,
  Building2,
  FileText,
} from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const DOCUMENT_TYPES = ['All', 'Policy', 'Circular', 'Certificate', 'Report', 'SOP', 'Handbook', 'Document']

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { toast } = useApp()
  const initialQ = searchParams.get('q') || ''
  const [query, setQuery] = useState(initialQ)
  const [dept, setDept] = useState('All')
  const [year, setYear] = useState('All')
  const [docType, setDocType] = useState('All')
  const [status, setStatus] = useState('All')
  const [selected, setSelected] = useState(null)
  const [results, setResults] = useState([])
  const [departments, setDepartments] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchResults = useCallback(async (q) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      const [searchData, deptData] = await Promise.all([
        api(`/api/search?${params}`),
        api('/api/repository/departments'),
      ])
      setResults(searchData.results || [])
      setDepartments(deptData.departments || [])
    } catch {
      setResults([])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchResults(initialQ)
  }, [initialQ, fetchResults])

  const filtered = useMemo(() => {
    return results.filter((r) => {
      const matchDept = dept === 'All' || r.department === dept
      const matchYear = year === 'All' || r.year === year
      const matchType = docType === 'All' || r.type === docType
      const matchStatus = status === 'All' || r.status === status
      return matchDept && matchYear && matchType && matchStatus
    })
  }, [results, dept, year, docType, status])

  const years = useMemo(() => {
    const y = [...new Set(results.map((r) => r.year).filter(Boolean))]
    return ['All', ...y.sort().reverse()]
  }, [results])

  function handleSearch(e) {
    e.preventDefault()
    setSearchParams(query.trim() ? { q: query.trim() } : {})
    setSelected(null)
  }

  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Knowledge Search</h1>
        <p className="mt-1 text-sm text-slate-500">
          Search policies, circulars, certificates and SOPs across your school
        </p>
      </div>

      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search school knowledge… e.g. leave policy, fire safety, fee structure"
            className="w-full rounded-xl border border-slate-200 bg-white py-3.5 pl-12 pr-28 text-base text-slate-800 shadow-sm placeholder:text-slate-400 outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100"
          />
          <button
            type="submit"
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg bg-navy-900 px-4 py-2 text-sm font-medium text-white hover:bg-navy-800"
          >
            Search
          </button>
        </div>
      </form>

      <div className="grid gap-6 lg:grid-cols-12">
        <aside className="lg:col-span-2">
          <Card className="sticky top-20 space-y-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
              <Filter className="h-4 w-4 text-navy-600" />
              Filters
            </div>
            <FilterSelect label="Department" value={dept} onChange={setDept} options={['All', ...departments.map(d => d.name)]} />
            <FilterSelect label="Academic Year" value={year} onChange={setYear} options={years} />
            <FilterSelect label="Document Type" value={docType} onChange={setDocType} options={DOCUMENT_TYPES} />
            <FilterSelect label="Status" value={status} onChange={setStatus} options={['All', 'Current', 'Expiring', 'Outdated', 'Missing']} />
            <button
              type="button"
              onClick={() => {
                setDept('All')
                setYear('All')
                setDocType('All')
                setStatus('All')
                toast('Filters cleared', 'info')
              }}
              className="w-full text-left text-xs font-medium text-navy-600 hover:text-navy-800"
            >
              Clear all filters
            </button>
          </Card>
        </aside>

        <div className="space-y-3 lg:col-span-6">
          <p className="text-sm text-slate-500">
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
                Searching…
              </span>
            ) : (
              <>
                <span className="font-semibold text-slate-700">{filtered.length}</span> results
                {query && (
                  <>
                    {' '}
                    for <span className="font-medium text-navy-800">&ldquo;{query}&rdquo;</span>
                  </>
                )}
              </>
            )}
          </p>
          {filtered.map((r) => (
            <Card
              key={r.id}
              className={`transition-all cursor-pointer ${selected?.id === r.id ? 'border-navy-400 ring-2 ring-navy-100' : ''}`}
              onClick={() =>
                r.source === 'student'
                  ? navigate(`/students/${r.id}`)
                  : setSelected(r)
              }
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h3 className="text-base font-semibold text-slate-900">{r.title}</h3>
                <StatusBadge status={r.status} />
              </div>
              <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-slate-600">{r.snippet}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <span className="inline-flex items-center gap-1 rounded-md bg-navy-50 px-2 py-1 font-medium text-navy-700">
                  <Building2 className="h-3 w-3" />
                  {r.department || '—'}
                </span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">{r.type}</span>
                <span className="rounded-md bg-slate-100 px-2 py-1 text-slate-600">{r.year}</span>
                {r.citation && (
                  <span className="inline-flex items-center gap-1 font-medium text-navy-600">
                    <ExternalLink className="h-3 w-3" />
                    {r.citation}
                  </span>
                )}
              </div>
            </Card>
          ))}
          {!loading && filtered.length === 0 && (
            <Card className="py-12 text-center">
              <FileText className="mx-auto h-10 w-10 text-slate-300" />
              <p className="mt-3 text-sm font-medium text-slate-600">No results found</p>
              <Button
                className="mt-4"
                variant="secondary"
                onClick={() => {
                  setQuery('')
                  setDept('All')
                  setYear('All')
                  setDocType('All')
                  setStatus('All')
                }}
              >
                Reset search
              </Button>
            </Card>
          )}
        </div>

        <aside className="space-y-4 lg:col-span-4">
          {selected ? (
            <Card>
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Selected document
              </p>
              <h3 className="mt-2 text-lg font-semibold text-slate-900">{selected.title}</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                <StatusBadge status={selected.status} />
                <span className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {selected.department || '—'}
                </span>
              </div>
              <dl className="mt-4 space-y-2 text-sm">
                {selected.citation && (
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Citation</dt>
                    <dd className="font-medium text-navy-700">{selected.citation}</dd>
                  </div>
                )}
                <div className="flex justify-between">
                  <dt className="text-slate-500">Owner</dt>
                  <dd className="font-medium text-slate-800">{selected.owner || '—'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Last updated</dt>
                  <dd className="font-medium text-slate-800">{selected.lastUpdated || '—'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Type</dt>
                  <dd className="font-medium text-slate-800">{selected.type}</dd>
                </div>
              </dl>
              <div className="mt-4 space-y-2">
                <Button
                  className="w-full"
                  onClick={() =>
                    navigate('/chat', { state: { seedQuestion: `Tell me about ${selected.title}` } })
                  }
                >
                  <MessageSquare className="h-4 w-4" />
                  Ask AI about this
                </Button>
                <Button
                  className="w-full"
                  variant="secondary"
                  onClick={() => navigate(`/document/${selected.id}`, { state: { doc: selected } })}
                >
                  Open full document
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="border-dashed py-8 text-center">
              <BookOpen className="mx-auto h-8 w-8 text-slate-300" />
              <p className="mt-2 text-sm text-slate-500">Select a result to preview details</p>
            </Card>
          )}

          <Card>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <BookOpen className="h-4 w-4 text-navy-600" />
              Related Knowledge
            </h3>
            <ul className="mt-3 space-y-2">
              {results.slice(0, 4).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() =>
                      item.source === 'student'
                        ? navigate(`/students/${item.id}`)
                        : setSelected(item)
                    }
                    className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-sm hover:bg-slate-50"
                  >
                    <span className="font-medium text-slate-700">{item.title}</span>
                    <span className="text-[10px] text-slate-400">{item.type}</span>
                  </button>
                </li>
              ))}
            </ul>
            <Link to="/library" className="mt-3 block text-xs font-medium text-navy-600 hover:underline">
              Browse full library →
            </Link>
          </Card>
        </aside>
      </div>
    </div>
  )
}

function FilterSelect({ label, value, onChange, options }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-sm text-slate-700 outline-none focus:border-navy-400 focus:ring-1 focus:ring-navy-100"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  )
}
