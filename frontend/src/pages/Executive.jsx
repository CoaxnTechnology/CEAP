import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  CheckSquare,
  AlertTriangle,
  Users,
  Shield,
  CalendarDays,
  Zap,
} from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Card from '../components/ui/Card'
import Section from '../components/ui/Section'
import Button from '../components/ui/Button'
import StatusBadge from '../components/ui/StatusBadge'
import InsightBanner from '../components/ui/InsightBanner'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'
import {
  morningBriefing,
  executiveKpis,
  tasks as seedTasks,
  approvals as seedApprovals,
  calendarEvents as seedEvents,
  students as seedStudents,
  quickActions,
  favorites,
} from '../data/osData'

const kpiConfig = {
  attendance: { id: 'attendance', label: 'Attendance', nav: '/academic', spark: [92, 93, 94, 95, 94, 96, 96.2] },
  revenue: { id: 'revenue', label: 'Fee collected (MTD)', nav: '/finance', spark: [30, 35, 38, 42, 44, 46, 48] },
  admissions: { id: 'admissions', label: 'Admissions pipeline', nav: '/admissions', spark: [40, 48, 52, 60, 68, 74, 86] },
  risk: { id: 'risk', label: 'At-risk students', nav: '/students', spark: [12, 11, 10, 9, 8, 7, 7] },
  approvals: { id: 'approvals', label: 'Pending approvals', nav: '/approvals', spark: [5, 6, 8, 7, 9, 10, 9] },
  compliance: { id: 'compliance', label: 'Inspection ready', nav: '/compliance', spark: [60, 62, 65, 68, 70, 72, 74] },
}

const kpiSeed = Object.fromEntries(executiveKpis.map((k) => [k.id, k]))

function initials(name) {
  return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

function partOfDay() {
  const h = new Date().getHours()
  if (h >= 5 && h < 12) return 'morning'
  if (h >= 12 && h < 17) return 'afternoon'
  if (h >= 17 && h < 21) return 'evening'
  return 'night'
}

function greetingForHour() {
  return {
    morning: 'Good morning',
    afternoon: 'Good afternoon',
    evening: 'Good evening',
    night: 'Good night',
  }[partOfDay()]
}

export default function Executive() {
  const { user, school } = useApp()
  const navigate = useNavigate()
  const [data, setData] = useState(null)

  useEffect(() => {
    api('/api/executive/overview')
      .then(setData)
      .catch(() => setData(null))
  }, [])

  const greeting = greetingForHour()
  const date = data?.date || morningBriefing.date
  const summary = data?.summary || morningBriefing.summary
  const bullets = data?.bullets || morningBriefing.bullets
  const recommendations = data?.recommendations?.length
    ? data.recommendations
    : [
        'Approve fee waiver for Kabir Sharma before SLA expires',
        'Start Fire Safety Certificate renewal workflow',
        'Counselor outreach for 2 high-risk Class 9–10 students',
      ]
  const kpis = kpiConfig
  const tasks = data?.tasks?.length ? data.tasks : seedTasks
  const openTasks = tasks.filter((t) => t.status !== 'Done')
  const pendingApprovals = data?.approvals?.length
    ? data.approvals
    : seedApprovals.filter((a) => a.status === 'Pending')
  const riskStudents = data?.riskStudents?.length
    ? data.riskStudents
    : seedStudents.filter((s) => s.riskLevel === 'High')
  const calendarEvents = data?.calendar?.length ? data.calendar : seedEvents.slice(0, 4)
  const complianceAlert = data?.complianceAlert || {
    message: 'Fire Safety Certificate expires in 18 days. Inspection readiness at 74%.',
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Executive Workspace"
        title={`${greeting}, ${user?.name?.split(' ')[0] || 'Principal'}`}
        subtitle={`${school?.name || 'Your school'} · ${date} · Your AI Operating System ${partOfDay()} screen`}
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => navigate('/approvals')}>
              <CheckSquare className="h-3.5 w-3.5" /> Approvals
            </Button>
            <Button size="sm" onClick={() => navigate('/ai')}>
              <Sparkles className="h-3.5 w-3.5" /> Open AI Studio
            </Button>
          </>
        }
      />

      {/* Morning briefing */}
      <Card className="relative overflow-hidden border-navy-100 bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800 text-white !p-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.12),transparent_50%)]" />
        <div className="relative grid gap-6 p-6 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-navy-100">
              <Sparkles className="h-3.5 w-3.5" /> AI Morning Briefing
            </div>
            <p className="text-base leading-relaxed text-navy-50 sm:text-lg">
              {summary}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Button
                size="sm"
                className="!bg-white !text-navy-900 hover:!bg-navy-50"
                onClick={() => navigate('/compliance')}
              >
                Fix compliance gap
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="!border-white/20 !bg-white/10 !text-white hover:!bg-white/20"
                onClick={() => navigate('/finance')}
              >
                Review collections
              </Button>
              <Button
                size="sm"
                variant="secondary"
                className="!border-white/20 !bg-white/10 !text-white hover:!bg-white/20"
                onClick={() => navigate('/students')}
              >
                At-risk students
              </Button>
            </div>
          </div>
          <div className="space-y-2 lg:col-span-2">
            {bullets.map((b, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-xl bg-white/8 px-3 py-2.5 text-sm text-navy-50 ring-1 ring-white/10"
              >
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                    b.type === 'success'
                      ? 'bg-emerald-400'
                      : b.type === 'warning'
                        ? 'bg-amber-400'
                        : b.type === 'alert'
                          ? 'bg-red-400'
                          : b.type === 'ai'
                            ? 'bg-violet-400'
                            : 'bg-sky-400'
                  }`}
                />
                {b.text}
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* KPIs */}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        {Object.entries(kpis).map(([key, cfg]) => {
          const live = data?.kpis?.[key]
          const seed = kpiSeed[key] || {}
          const value = live?.value ?? seed.value
          const delta = live?.delta ?? seed.delta
          const trend = live?.trend ?? seed.trend
          return (
            <KpiCard
              key={key}
              label={cfg.label}
              value={value}
              delta={delta}
              trend={trend}
              spark={cfg.spark}
              onClick={() => navigate(cfg.nav)}
            />
          )
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Quick actions + favorites */}
        <div className="space-y-6 lg:col-span-4">
          <Section title="Quick actions" subtitle="Operate the school in one click">
            <div className="grid grid-cols-2 gap-2">
              {quickActions.map((a) => (
                <button
                  key={a.path}
                  type="button"
                  onClick={() => navigate(a.path)}
                  className="flex items-center gap-2 rounded-xl border border-slate-100 bg-slate-50/80 px-3 py-3 text-left text-xs font-medium text-slate-700 transition hover:border-navy-200 hover:bg-white hover:shadow-sm"
                >
                  <Zap className="h-3.5 w-3.5 text-navy-500" />
                  {a.label}
                </button>
              ))}
            </div>
          </Section>

          <Section title="Pinned & favorites">
            <ul className="space-y-1">
              {favorites.map((f) => (
                <li key={f.path}>
                  <button
                    type="button"
                    onClick={() => navigate(f.path)}
                    className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    {f.label}
                    <ArrowRight className="h-3.5 w-3.5 text-slate-300" />
                  </button>
                </li>
              ))}
            </ul>
          </Section>

          <InsightBanner title="Principal AI recommends" items={recommendations} />
        </div>

        {/* Tasks + Approvals */}
        <div className="space-y-6 lg:col-span-5">
          <Section
            title="Priority tasks"
            subtitle={`${openTasks.length} open`}
            action={
              <button
                type="button"
                onClick={() => navigate('/tasks')}
                className="text-xs font-medium text-navy-600"
              >
                View all
              </button>
            }
            padding={false}
          >
            <ul className="divide-y divide-slate-50">
              {tasks.slice(0, 5).map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    onClick={() => navigate('/tasks')}
                    className="flex w-full items-start gap-3 px-5 py-3.5 text-left hover:bg-slate-50/80"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-800">{t.title}</p>
                      <p className="mt-0.5 text-[11px] text-slate-400">
                        {t.owner} · Due {t.due} · {t.workspace}
                      </p>
                    </div>
                    <StatusBadge
                      status={
                        t.priority === 'Urgent'
                          ? 'Missing'
                          : t.priority === 'High'
                            ? 'Expiring'
                            : 'Current'
                      }
                    />
                  </button>
                </li>
              ))}
            </ul>
          </Section>

          <Section
            title="Pending approvals"
            action={
              <button type="button" onClick={() => navigate('/approvals')} className="text-xs font-medium text-navy-600">
                Inbox
              </button>
            }
            padding={false}
          >
            <ul className="divide-y divide-slate-50">
              {pendingApprovals.map((a) => (
                <li key={a.id} className="flex items-center gap-3 px-5 py-3.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-slate-800">{a.title}</p>
                    <p className="text-[11px] text-slate-400">
                      {a.type} · {a.requester} · {a.sla}
                    </p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => navigate('/approvals')}>
                    Review
                  </Button>
                </li>
              ))}
            </ul>
          </Section>
        </div>

        {/* Risk + calendar */}
        <div className="space-y-6 lg:col-span-3">
          <Section title="Student risk pulse" action={<Users className="h-4 w-4 text-navy-500" />}>
            <ul className="space-y-3">
              {riskStudents.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => navigate(`/students/${s.id}`)}
                  className="flex w-full items-center gap-3 rounded-xl border border-slate-100 p-2.5 text-left hover:border-navy-200"
                >
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-danger-50 text-xs font-bold text-danger-600">
                    {s.photo || initials(s.name)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-800">{s.name}</p>
                    <p className="text-[11px] text-slate-400">
                      {s.class} · Risk {s.riskScore}
                    </p>
                  </div>
                  <AlertTriangle className="h-4 w-4 text-warning-500" />
                </button>
              ))}
            </ul>
            <Button className="mt-3 w-full" variant="secondary" size="sm" onClick={() => navigate('/students')}>
              Student 360
            </Button>
          </Section>

          <Section title="Upcoming" action={<CalendarDays className="h-4 w-4 text-navy-500" />}>
            <ul className="space-y-2">
              {calendarEvents.slice(0, 4).map((e) => (
                <li key={e.id} className="flex gap-3 text-sm">
                  <div className="w-14 shrink-0 text-[11px] font-medium text-navy-600">
                    {e.date.slice(5)}
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">{e.title}</p>
                    <p className="text-[11px] text-slate-400">
                      {e.time} · {e.type}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={() => navigate('/calendar')}
              className="mt-3 text-xs font-medium text-navy-600"
            >
              Open calendar →
            </button>
          </Section>

          <Card className="border-amber-100 bg-amber-50/50">
            <div className="flex items-start gap-2">
              <Shield className="mt-0.5 h-4 w-4 text-amber-600" />
              <div>
                <p className="text-sm font-semibold text-amber-900">Compliance alert</p>
                <p className="mt-1 text-xs text-amber-800/80">
                  {complianceAlert.message}
                </p>
                <Button size="sm" className="mt-3" onClick={() => navigate('/compliance')}>
                  Open Compliance Center
                </Button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
