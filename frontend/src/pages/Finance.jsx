import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Pencil } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Section from '../components/ui/Section'
import InsightBanner from '../components/ui/InsightBanner'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import Modal from '../components/ui/Modal'
import WorkflowQuickStart from '../components/WorkflowQuickStart'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

const inrLakhs = (v) => `₹${(v / 100000).toFixed(1)}L`

export default function Finance() {
  const navigate = useNavigate()
  const { toast, dispatch } = useApp()
  const [data, setData] = useState(null)
  const [waiver, setWaiver] = useState(null)
  const [collections, setCollections] = useState(null)
  const [savingCol, setSavingCol] = useState(false)
  const [riskClass, setRiskClass] = useState('All')
  const [riskPage, setRiskPage] = useState(1)
  const RISK_PAGE_SIZE = 10

  const load = () =>
    api('/api/finance/overview')
      .then(setData)
      .catch(() => toast('Could not load finance data', 'warning'))

  useEffect(() => {
    load()
  }, [])

  function runOutreach() {
    api('/api/finance/outreach', { method: 'POST' })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: 'Launched',
            target: 'Collection campaign',
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(res.message, 'success')
      })
      .catch(() => toast('Could not launch outreach', 'warning'))
  }

  function submitWaiver(e) {
    e.preventDefault()
    api('/api/finance/waivers', {
      method: 'POST',
      body: JSON.stringify(waiver),
    })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: 'Requested',
            target: `Fee waiver for ${waiver.studentName}`,
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(res.message, 'success')
        setWaiver(null)
      })
      .catch(() => toast('Could not submit fee waiver', 'warning'))
  }

  const openCollections = () => {
    setCollections(
      data.trend.labels.map((month, i) => ({
        month,
        amountLakhs: data.trend.values[i] ?? 0,
      }))
    )
  }

  const saveCollections = async () => {
    if (!collections) return
    setSavingCol(true)
    try {
      await api('/api/finance/collections', { method: 'PUT', body: JSON.stringify(collections) })
      setCollections(null)
      await load()
      toast('Collection trend updated', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSavingCol(false)
    }
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-7xl">
        <PageHeader eyebrow="Finance Workspace" title="Finance Intelligence" subtitle="Loading…" />
      </div>
    )
  }

  const pct = Math.round((data.kpis.mtdCollected / data.kpis.target) * 100)
  const maxBar = Math.max(...data.outstandingByClass.map((x) => x.amount))

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Finance Workspace"
        title="Finance Intelligence"
        subtitle="Revenue, risk, and forecasts — not a fee receipt ledger. Operate collections with AI."
        actions={
          <>
            <WorkflowQuickStart workflowKey="purchase" label="Purchase" />
            <WorkflowQuickStart workflowKey="fee-waiver" label="Fee waiver" />
            <Button variant="secondary" size="sm" onClick={runOutreach}>
              Run outreach
            </Button>
            <Button size="sm" onClick={() => navigate('/ai/chat', { state: { seedQuestion: 'Explain fee outstanding and predicted defaulters' } })}>
              Ask Finance AI
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Collected MTD" value={inrLakhs(data.kpis.mtdCollected)} delta={`${pct}% of target`} trend="down" spark={data.trend.values} />
        <KpiCard label="Outstanding" value={inrLakhs(data.kpis.outstanding)} delta={`${data.kpis.families} families`} trend="warn" spark={[18, 16, 15, 14, 13, 12.8, 12.4]} />
        <KpiCard label="Predicted defaulters" value={String(data.kpis.predictedDefaulters)} delta="Next 30 days" trend="warn" spark={[22, 21, 20, 19, 19, 18, 18]} />
        <KpiCard label="Scholarships active" value={String(data.kpis.scholarships)} delta={inrLakhs(data.kpis.scholarshipBudgetLeft) + ' budget left'} trend="up" spark={[5, 6, 6, 7, 8, 8, 8]} />
      </div>

      <InsightBanner title="Finance AI Insights" items={data.insights} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Section
          title="Collection trend"
          subtitle="₹ Lakhs"
          action={
            <Button size="sm" variant="secondary" onClick={openCollections}>
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
          }
        >
          <div className="flex h-40 gap-2">
            {data.trend.values.map((v, i) => (
              <div key={i} className="flex flex-1 flex-col items-center justify-end gap-1">
                <div
                  className="w-full rounded-t-lg bar-gradient"
                  style={{ height: `${(v / 55) * 100}%` }}
                />
                <span className="text-[10px] text-slate-400">{data.trend.labels[i]}</span>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Outstanding by class" subtitle="₹ Lakhs">
          <div className="space-y-3">
            {data.outstandingByClass.map((row) => (
              <div key={row.cls}>
                <div className="mb-1 flex justify-between text-xs">
                  <span className="font-medium text-slate-700">Class {row.cls}</span>
                  <span className="text-slate-500">₹{row.amount}L</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500"
                    style={{ width: `${(row.amount / maxBar) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Section>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="card-hover" onClick={() => navigate('/students')}>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Action</p>
          <p className="mt-2 font-semibold text-slate-900">Open student fee risk</p>
          <p className="mt-1 text-xs text-slate-500">Students for family-level follow-up</p>
        </Card>
        <Card className="card-hover" onClick={() => navigate('/approvals')}>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Action</p>
          <p className="mt-2 font-semibold text-slate-900">Fee waiver approvals</p>
          <p className="mt-1 text-xs text-slate-500">Human-in-the-loop before write-offs</p>
        </Card>
        <Card className="card-hover" onClick={() => navigate('/analytics')}>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Action</p>
          <p className="mt-2 font-semibold text-slate-900">Full analytics</p>
          <p className="mt-1 text-xs text-slate-500">BI trends across years</p>
        </Card>
      </div>

      <Modal
        open={!!collections}
        onClose={() => setCollections(null)}
        title="Edit collection trend (₹ Lakhs)"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setCollections(null)}>Cancel</Button>
            <Button size="sm" onClick={saveCollections} disabled={savingCol}>
              {savingCol ? 'Saving…' : 'Save'}
            </Button>
          </>
        }
      >
        <div className="grid grid-cols-2 gap-3">
          {collections?.map((c, i) => (
            <div key={c.month}>
              <label className="mb-1 block text-xs font-medium text-slate-500">{c.month}</label>
              <input
                type="number"
                step="0.1"
                min="0"
                className="field"
                value={c.amountLakhs}
                onChange={(e) => {
                  const next = [...collections]
                  next[i] = { ...c, amountLakhs: Number(e.target.value) || 0 }
                  setCollections(next)
                }}
              />
            </div>
          ))}
        </div>
      </Modal>

      <Section
        title="Student fee risk"
        action={
          <select
            value={riskClass}
            onChange={(e) => { setRiskClass(e.target.value); setRiskPage(1) }}
            className="field sm:w-40"
          >
            <option value="All">All classes</option>
            {[...new Set((data.riskFamilies || []).map((s) => s.className))].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        }
      >
        <div className="mx-auto max-w-2xl">
          <ul className="divide-y divide-slate-50">
            {(data.riskFamilies || [])
              .filter((s) => riskClass === 'All' || s.className === riskClass)
              .slice((riskPage - 1) * RISK_PAGE_SIZE, riskPage * RISK_PAGE_SIZE)
              .map((s) => (
            <li key={s.studentName} className="flex items-center justify-between gap-3 py-2.5">
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800">
                  {s.studentName}
                  {s.predictedDefault && (
                    <span className="ml-2 rounded bg-red-50 px-1.5 py-0.5 text-[10px] font-semibold text-red-600">
                      Predicted defaulter
                    </span>
                  )}
                </p>
                <p className="text-[11px] text-slate-400">
                  Class {s.className} · {s.familyEmail} · {s.overdueDays}d overdue
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <span className="text-sm font-semibold text-slate-900">{inrLakhs(s.outstanding)}</span>
                <Button size="sm" variant="secondary" onClick={() => setWaiver({ ...s, amount: '', reason: '' })}>
                  Request waiver
                </Button>
              </div>
            </li>
          ))}
          </ul>
          {(() => {
            const total = (data.riskFamilies || []).filter((s) => riskClass === 'All' || s.className === riskClass).length
            const pages = Math.max(1, Math.ceil(total / RISK_PAGE_SIZE))
            if (pages <= 1) return null
            return (
              <div className="mt-3 flex items-center justify-between">
                <p className="text-xs text-slate-400">
                  {total} families · page {riskPage} of {pages}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" disabled={riskPage <= 1} onClick={() => setRiskPage((p) => Math.max(1, p - 1))}>
                    Previous
                  </Button>
                  <Button size="sm" variant="secondary" disabled={riskPage >= pages} onClick={() => setRiskPage((p) => Math.min(pages, p + 1))}>
                    Next
                  </Button>
                </div>
              </div>
            )
          })()}
        </div>
      </Section>

      <Modal
        open={!!waiver}
        onClose={() => setWaiver(null)}
        title={`Fee waiver — ${waiver?.studentName || ''}`}
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setWaiver(null)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="waiver-form">
              Submit for approval
            </Button>
          </>
        }
      >
        <form id="waiver-form" onSubmit={submitWaiver} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Waiver amount (₹)</label>
            <input
              type="number"
              min="0"
              className="field"
              value={waiver?.amount ?? ''}
              onChange={(e) => setWaiver((w) => ({ ...w, amount: e.target.value }))}
              placeholder={`Outstanding ${inrLakhs(waiver?.outstanding || 0)}`}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Reason</label>
            <textarea
              className="field"
              rows="3"
              value={waiver?.reason ?? ''}
              onChange={(e) => setWaiver((w) => ({ ...w, reason: e.target.value }))}
              placeholder="e.g. Medical hardship — family requested support"
            />
          </div>
        </form>
      </Modal>
    </div>
  )
}
