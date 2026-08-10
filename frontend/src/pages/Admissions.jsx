import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, GripVertical } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import InsightBanner from '../components/ui/InsightBanner'
import WorkflowQuickStart from '../components/WorkflowQuickStart'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

const stages = ['Applied', 'Tour', 'Interview', 'Offer', 'Enrolled']

export default function Admissions() {
  const { toast, dispatch } = useApp()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [showNew, setShowNew] = useState(false)
  const [dragId, setDragId] = useState(null)
  const [form, setForm] = useState({ studentName: '', grade: '', parentName: '', parentContact: '' })

  const load = () =>
    api('/api/admissions/overview')
      .then(setData)
      .catch(() => toast('Could not load admissions data', 'warning'))

  useEffect(() => {
    load()
  }, [])

  function advance(id, name) {
    api(`/api/admissions/${id}/advance`, { method: 'POST' })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: 'Advanced',
            target: `${name} → ${res.stage}`,
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(`${name} → ${res.stage}`, 'success')
        if (res.student_id) {
          navigate(`/students/${res.student_id}`, {
            state: { student: { id: res.student_id, name, class: res.grade } },
          })
        }
        return load()
      })
      .catch((e) => toast(e.message || 'Could not advance', 'warning'))
  }

  function viewStudent(studentId, name, grade) {
    navigate(`/students/${studentId}`, {
      state: { student: { id: studentId, name, class: grade } },
    })
  }

  function remove(id, name) {
    if (!window.confirm(`Remove ${name} from the pipeline?`)) return
    api(`/api/admissions/${id}`, { method: 'DELETE' })
      .then(() => {
        toast(`Removed ${name}`, 'info')
        return load()
      })
      .catch(() => toast('Could not remove applicant', 'warning'))
  }

  function move(id, stage) {
    api(`/api/admissions/${id}`, { method: 'PATCH', body: JSON.stringify({ stage }) })
      .then(() => {
        toast(`Moved to ${stage}`, 'success')
        return load()
      })
      .catch(() => toast('Could not move applicant', 'warning'))
  }

  function submitInquiry(e) {
    e.preventDefault()
    if (!form.studentName) {
      toast('Applicant name is required', 'warning')
      return
    }
    api('/api/admissions', { method: 'POST', body: JSON.stringify(form) })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: 'Logged',
            target: `Inquiry — ${res.name}`,
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(`Inquiry logged: ${res.name}`, 'success')
        setShowNew(false)
        setForm({ studentName: '', grade: '', parentName: '', parentContact: '' })
        return load()
      })
      .catch((e) => toast(e.message || 'Could not log inquiry', 'warning'))
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-7xl">
        <PageHeader eyebrow="Admissions Workspace" title="Admissions Intelligence" subtitle="Loading…" />
      </div>
    )
  }

  const pipeline = data.pipeline
  const applications = data.applications || pipeline

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Admissions Workspace"
        title="Admissions Intelligence"
        subtitle="Pipeline, conversion, and counselor load — AI scores applicants, humans decide offers."
        actions={
          <>
            <WorkflowQuickStart workflowKey="admission" label="Start admission" />
            <Button size="sm" onClick={() => setShowNew(true)}>
              New inquiry
            </Button>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Applied" value={String(data.stats.applied)} trend="up" delta="+6" spark={[20, 25, 30, 34, 38, 40, 42]} />
        <KpiCard label="Interview" value={String(data.stats.interview)} trend="up" delta="This week" spark={[8, 10, 12, 14, 15, 16, 18]} />
        <KpiCard label="Offers" value={String(data.stats.offer)} trend="flat" delta="Out" spark={[6, 7, 8, 9, 10, 11, 12]} />
        <KpiCard label="Enrolled" value={String(data.stats.enrolled)} trend="up" delta={data.stats.conversion} spark={[5, 6, 8, 9, 11, 12, 14]} />
        <KpiCard label="Seats filled" value={`${data.stats.filled}/${data.stats.targetSeats}`} trend="up" delta="Target" spark={[40, 50, 60, 70, 78, 82, 86]} />
      </div>

      <InsightBanner title="Admissions AI" items={data.insights} />

      <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-5">
        {stages.map((stage) => (
          <div
            key={stage}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              if (dragId) move(dragId, stage)
            }}
            className="rounded-2xl border border-slate-200 bg-white p-3"
          >
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              {stage}{' '}
              <span className="text-slate-300">
                ({pipeline.filter((p) => p.stage === stage).length})
              </span>
            </p>
            <div className="space-y-2 min-h-[60px]">
              {pipeline
                .filter((p) => p.stage === stage && !p.removed_at)
                .map((p) => (
                  <div
                    key={p.id}
                    draggable
                    onDragStart={() => setDragId(p.id)}
                    onDragEnd={() => setDragId(null)}
                    onClick={() =>
                      p.stage === 'Enrolled'
                        ? viewStudent(p.student_id, p.name, p.grade)
                        : advance(p.id, p.name)
                    }
                    className={`group relative w-full cursor-grab rounded-xl border p-3 text-left transition active:cursor-grabbing ${
                      p.stage === 'Enrolled'
                        ? 'border-emerald-200 bg-emerald-50/80 hover:border-emerald-300 hover:bg-emerald-100'
                        : 'border-slate-100 bg-slate-50/80 hover:border-navy-200 hover:bg-white hover:shadow-sm'
                    }`}
                  >
                    <GripVertical className="absolute left-1 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-300 opacity-0 transition group-hover:opacity-100" />
                    <button
                      type="button"
                      title={`Remove ${p.name}`}
                      onClick={(e) => {
                        e.stopPropagation()
                        remove(p.id, p.name)
                      }}
                      className="absolute right-1.5 top-1.5 rounded p-1 text-slate-300 opacity-0 transition hover:bg-danger-50 hover:text-danger-600 group-hover:opacity-100"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                    <p className="text-sm font-semibold text-slate-900">{p.name}</p>
                    <p className="text-[11px] text-slate-500">
                      Grade {p.grade} · Score {p.score || '—'}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-400">{p.counselor || 'Unassigned'}</p>
                    {p.stage === 'Enrolled' && (
                      <span className="mt-1 inline-block text-[10px] font-medium text-emerald-700">
                        View Student →
                      </span>
                    )}
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>

      <Section title="All applications" padding={false}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs uppercase text-slate-400">
                <th className="px-5 py-3">Applicant</th>
                <th className="px-3 py-3">Grade</th>
                <th className="px-3 py-3">Stage</th>
                <th className="px-3 py-3">AI score</th>
                <th className="px-3 py-3">Counselor</th>
                <th className="px-5 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {applications.map((p) => (
                <tr key={p.id} className="hover:bg-slate-50">
                  <td className="px-5 py-3 font-medium">
                    {p.name}
                    {p.removed_at && (
                      <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold text-slate-400">
                        Removed · purges in 24h
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-3">{p.grade}</td>
                  <td className="px-3 py-3">
                    <StatusBadge status={p.removed_at ? 'Draft' : p.stage === 'Enrolled' ? 'Current' : p.stage === 'Offer' ? 'Expiring' : 'Draft'} />
                    <span className="ml-1 text-xs text-slate-500">{p.stage}</span>
                  </td>
                  <td className="px-3 py-3 font-semibold text-navy-800">{p.score || '—'}</td>
                  <td className="px-3 py-3 text-slate-500">{p.counselor || '—'}</td>
                  <td className="px-5 py-3 text-slate-500">{p.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Modal
        open={showNew}
        onClose={() => setShowNew(false)}
        title="New inquiry"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setShowNew(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" form="inquiry-form">
              Log inquiry
            </Button>
          </>
        }
      >
        <form id="inquiry-form" onSubmit={submitInquiry} className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Student name *</label>
            <input
              className="field"
              value={form.studentName}
              onChange={(e) => setForm((f) => ({ ...f, studentName: e.target.value }))}
              placeholder="e.g. Ishaan Rao"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Grade</label>
            <input
              className="field"
              value={form.grade}
              onChange={(e) => setForm((f) => ({ ...f, grade: e.target.value }))}
              placeholder="e.g. Nursery, 1, 6"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Parent name</label>
              <input
                className="field"
                value={form.parentName}
                onChange={(e) => setForm((f) => ({ ...f, parentName: e.target.value }))}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Contact</label>
              <input
                className="field"
                value={form.parentContact}
                onChange={(e) => setForm((f) => ({ ...f, parentContact: e.target.value }))}
                placeholder="+91 …"
              />
            </div>
          </div>
        </form>
      </Modal>

      <style>{`.field{width:100%;border-radius:.5rem;border:1px solid #e2e8f0;background:#f8fafc;padding:.55rem .75rem;font-size:.875rem;outline:none}.field:focus{border-color:#7c3aed;background:#fff;box-shadow:0 0 0 2px #ddd6fe}`}</style>
    </div>
  )
}
