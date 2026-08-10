import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import KpiCard from '../components/ui/KpiCard'
import Section from '../components/ui/Section'
import { analyticsBundles as seedBundles, executiveKpis, financeIntel, academicIntel } from '../data/osData'
import { api } from '../lib/api'

const seedByClass = Object.fromEntries(financeIntel.outstandingByClass.map((r) => [r.cls, r.amount]))
const seedDepts = academicIntel.departments

export default function Analytics() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)

  useEffect(() => {
    Promise.all([
      api('/api/executive/overview').catch(() => null),
      api('/api/finance/overview').catch(() => null),
      api('/api/academic/overview').catch(() => null),
    ]).then(([exec, fin, acad]) => {
      const kp = exec?.kpis || {}
      const att = acad?.stats?.avgClassAttendance ?? kp?.attendance?.value
      const heatmap = (fin?.outstandingByClass || []).map((r) => ({
        cls: r.cls,
        amount: seedByClass[r.cls] ?? r.amount,
      }))
      const bundles = seedBundles.map((b) => {
        if (b.id === 'fee' && fin?.kpis?.mtdCollected) {
          return { ...b, value: `₹${(fin.kpis.mtdCollected / 100000).toFixed(1)}L`, change: kp?.revenue?.delta || b.change }
        }
        if (b.id === 'attendance' && att) {
          return { ...b, value: `${att}%`, change: kp?.attendance?.delta || b.change }
        }
        if (b.id === 'inspection' && kp?.compliance?.value) {
          return { ...b, value: kp.compliance.value, change: kp.compliance.delta || b.change }
        }
        if (b.id === 'admissions' && kp?.admissions?.value) {
          return { ...b, value: kp.admissions.value, change: b.change }
        }
        return b
      })
      const sparklines = executiveKpis.slice(0, 4).map((k) => {
        if (k.id === 'attendance' && att) return { ...k, value: `${att}%`, delta: kp?.attendance?.delta || k.delta }
        if (k.id === 'revenue' && kp?.revenue?.value) return { ...k, value: kp.revenue.value, delta: kp.revenue.delta, trend: kp.revenue.trend }
        if (k.id === 'admissions' && kp?.admissions?.value) return { ...k, value: kp.admissions.value, delta: kp.admissions.delta || k.delta }
        if (k.id === 'risk' && kp?.risk?.value) return { ...k, value: kp.risk.value, delta: kp.risk.delta || k.delta }
        return k
      })
      setData({
        bundles,
        sparklines,
        feeHeatmap: heatmap.length ? heatmap : financeIntel.outstandingByClass,
        departments: acad?.departments?.length ? acad.departments.map((d) => ({
          name: d.name,
          coverage: d.coverage ?? seedDepts.find((s) => s.name === d.name)?.coverage ?? 0,
          attendance: d.attendance ?? seedDepts.find((s) => s.name === d.name)?.attendance ?? 0,
          risk: d.risk ?? 0,
        })) : seedDepts,
      })
    })
  }, [])

  const bundles = data?.bundles || seedBundles
  const sparklines = data?.sparklines || executiveKpis.slice(0, 4)
  const feeHeatmap = data?.feeHeatmap || financeIntel.outstandingByClass
  const departments = data?.departments || seedDepts

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Analytics"
        subtitle="Beautiful BI across academic, fee, attendance, inspection, and admissions trends."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {bundles.map((b) => (
          <Card
            key={b.id}
            className="card-hover"
            onClick={() => {
              if (b.id === 'fee') navigate('/finance')
              else if (b.id === 'academic' || b.id === 'attendance') navigate('/academic')
              else if (b.id === 'inspection') navigate('/compliance')
              else if (b.id === 'admissions') navigate('/admissions')
              else if (b.id === 'hr') navigate('/hr')
            }}
          >
            <p className="text-xs font-medium text-slate-500">{b.title}</p>
            <p className="mt-1 text-[11px] text-slate-400">{b.metric}</p>
            <div className="mt-2 flex items-end justify-between">
              <p className="text-2xl font-bold text-slate-900">{b.value}</p>
              <span className="text-xs font-semibold text-navy-600">{b.change}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Executive KPI sparklines">
          <div className="grid gap-3 sm:grid-cols-2">
            {sparklines.map((k) => (
              <KpiCard key={k.id} {...k} />
            ))}
          </div>
        </Section>
        <Section title="Fee heatmap (by class)">
          <div className="grid grid-cols-3 gap-2">
            {feeHeatmap.map((r) => (
              <div
                key={r.cls}
                className="flex aspect-square flex-col items-center justify-center rounded-xl text-white"
                style={{
                  backgroundColor: `rgba(180, 83, 9, ${0.35 + (r.amount / 4) * 0.5})`,
                }}
              >
                <span className="text-lg font-bold">{r.cls}</span>
                <span className="text-[10px]">₹{r.amount}L</span>
              </div>
            ))}
          </div>
        </Section>
      </div>

      <Section title="Department attendance vs coverage">
        <div className="space-y-3">
          {departments.map((d) => (
            <div key={d.name} className="grid grid-cols-12 items-center gap-2 text-sm">
              <span className="col-span-3 font-medium text-slate-700">{d.name}</span>
              <div className="col-span-4 h-2 rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-navy-600" style={{ width: `${d.coverage}%` }} />
              </div>
              <div className="col-span-4 h-2 rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${d.attendance}%` }} />
              </div>
              <span className="col-span-1 text-[10px] text-slate-400">risk {d.risk}</span>
            </div>
          ))}
          <div className="flex gap-4 text-[10px] text-slate-400">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-navy-600" /> Coverage
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Attendance
            </span>
          </div>
        </div>
      </Section>
    </div>
  )
}
