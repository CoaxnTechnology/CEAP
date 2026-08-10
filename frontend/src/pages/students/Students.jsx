import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Search, Users, AlertTriangle } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import KpiCard from '../../components/ui/KpiCard'
import InsightBanner from '../../components/ui/InsightBanner'
import { api } from '../../lib/api'

export default function Students() {
  const navigate = useNavigate()
  const location = useLocation()
  const [students, setStudents] = useState([])
  const [q, setQ] = useState('')
  const [risk, setRisk] = useState('All')

  useEffect(() => {
    if (location.state?.risk) {
      setRisk(location.state.risk)
    }
  }, [location.state])

  useEffect(() => {
    api('/api/students')
      .then((d) => setStudents(d.students || []))
      .catch(() => setStudents([]))
  }, [])

  const list = useMemo(() => {
    return students.filter((s) => {
      const matchQ =
        !q ||
        s.name.toLowerCase().includes(q.toLowerCase()) ||
        s.class.toLowerCase().includes(q.toLowerCase()) ||
        s.admissionNo.toLowerCase().includes(q.toLowerCase())
      const matchR = risk === 'All' || s.riskLevel === risk
      return matchQ && matchR
    })
  }, [q, risk, students])

  const high = students.filter((s) => s.riskLevel === 'High').length
  const overdue = students.filter((s) => s.feesStatus === 'Overdue').length

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Student Workspace"
        title="Students"
        subtitle="Student 360 — risk, success, documents, and AI recommendations. Not an SIS form grid."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Active students" value={String(students.length)} delta="Cohort" trend="flat" spark={[3, 4, 4, 5, 5, 5, 5]} />
        <KpiCard label="High risk" value={String(high)} delta="Needs intervention" trend="warn" spark={[5, 4, 4, 3, 3, 2, 2]} />
        <KpiCard label="Fee overdue" value={String(overdue)} delta="Families" trend="down" spark={[4, 4, 3, 3, 3, 2, 2]} />
        <KpiCard label="Avg attendance" value="89%" delta="Cohort" trend="flat" spark={[88, 87, 89, 90, 88, 89, 89]} />
      </div>

      <InsightBanner
        title="Student Success AI"
        items={[
          '2 students require counselor + finance coordination this week',
          'Cross-signal: low attendance often co-occurs with fee stress',
          'Open any profile for timeline, vault, and AI action plan',
        ]}
      />

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search name, class, admission no…"
            className="field !pl-10"
          />
        </div>
        <select value={risk} onChange={(e) => setRisk(e.target.value)} className="field sm:w-40">
          <option value="All">All risk</option>
          <option>High</option>
          <option>Medium</option>
          <option>Low</option>
        </select>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {list.map((s) => (
          <Card key={s.id} className="card-hover" onClick={() => navigate(`/students/${s.id}`, { state: { student: s } })}>
            <div className="flex items-start gap-3">
              <div
                className={`flex h-12 w-12 items-center justify-center rounded-2xl text-sm font-bold text-white ${
                  s.riskLevel === 'High'
                    ? 'bg-gradient-to-br from-red-500 to-red-700'
                    : s.riskLevel === 'Medium'
                      ? 'bg-gradient-to-br from-amber-500 to-amber-700'
                      : 'bg-gradient-to-br from-navy-600 to-navy-900'
                }`}
              >
                {s.photo}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-slate-900">{s.name}</h3>
                    <p className="text-xs text-slate-500">
                      {s.class} · {s.roll}
                    </p>
                  </div>
                  {s.riskLevel === 'High' && <AlertTriangle className="h-4 w-4 text-warning-500" />}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <StatusBadge
                    status={
                      s.riskLevel === 'High' ? 'Missing' : s.riskLevel === 'Medium' ? 'Expiring' : 'Current'
                    }
                  />
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                    Risk {s.riskScore}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                    Att {s.attendance}%
                  </span>
                </div>
                <p className="mt-3 line-clamp-2 text-xs leading-relaxed text-slate-500">{s.aiSummary}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {list.length === 0 && (
        <div className="py-12 text-center text-sm text-slate-400">
          <Users className="mx-auto mb-2 h-8 w-8 opacity-40" />
          No students match
        </div>
      )}
    </div>
  )
}
