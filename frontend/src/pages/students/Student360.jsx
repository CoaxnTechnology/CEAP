import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  FileText,
  Phone,
  Mail,
  Download,
  MessageSquare,
  CalendarPlus,
  RefreshCw,
  Pencil,
  Plus,
  Trash2,
} from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import Section from '../../components/ui/Section'
import Button from '../../components/ui/Button'
import StatusBadge from '../../components/ui/StatusBadge'
import InsightBanner from '../../components/ui/InsightBanner'
import Modal from '../../components/ui/Modal'
import { useApp } from '../../context/AppContext'
import { api } from '../../lib/api'

const tabs = ['Overview', 'Timeline', 'Documents', 'Academics', 'Fees', 'Medical', 'Communication']

export default function Student360() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { toast, dispatch, user } = useApp()
  const [tab, setTab] = useState('Overview')
  const [detail, setDetail] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [composing, setComposing] = useState(false)
  const [msg, setMsg] = useState({ channel: 'call', subject: '', body: '' })
  const [communications, setCommunications] = useState([])
  const [documents, setDocuments] = useState([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [marksOpen, setMarksOpen] = useState(false)
  const [draftMarks, setDraftMarks] = useState([])
  const [savingMarks, setSavingMarks] = useState(false)
  const [feesOpen, setFeesOpen] = useState(false)
  const [draftFees, setDraftFees] = useState({ feesDue: 0, feesStatus: 'Cleared' })
  const [feeSaving, setFeeSaving] = useState(false)
  const [payment, setPayment] = useState({ amount: '', date: '' })
  const [paySaving, setPaySaving] = useState(false)
  const [payOpen, setPayOpen] = useState(false)
  const [form, setForm] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (detail) setForm(JSON.parse(JSON.stringify(detail)))
  }, [detail])

  useEffect(() => {
    api(`/api/students/${id}`)
      .then((d) => setDetail(d))
      .catch(() => setNotFound(true))
  }, [id])

  useEffect(() => {
    if (tab === 'Communication' && detail) {
      api(`/api/students/${id}/communications`)
        .then((d) => setCommunications(d.communications || []))
        .catch(() => setCommunications([]))
    }
  }, [tab, id, detail])

  useEffect(() => {
    if (tab === 'Documents' && detail) {
      setDocsLoading(true)
      api(`/api/students/${id}/documents`)
        .then((d) => setDocuments(Object.values(d.documents || {})))
        .catch(() => setDocuments([]))
        .finally(() => setDocsLoading(false))
    }
  }, [tab, id, detail])

  const syncVault = async () => {
    setSyncing(true)
    try {
      const res = await api(`/api/students/${id}/documents/sync`, { method: 'POST' })
      toast(`Synced ${res.synced?.length || 0} documents`, 'success')
      const d = await api(`/api/students/${id}/documents`)
      setDocuments(Object.values(d.documents || {}))
    } catch {
      toast('Sync failed', 'error')
    } finally {
      setSyncing(false)
    }
  }

  const s = detail

  const setF = (key, value) => setForm((f) => ({ ...f, [key]: value }))
  const setParent = (key, value) => setForm((f) => ({ ...f, parent: { ...f.parent, [key]: value } }))
  const setMedical = (key, value) => setForm((f) => ({ ...f, medical: { ...f.medical, [key]: value } }))

  const save = async () => {
    if (!form) return
    setSaving(true)
    try {
      const updated = await api(`/api/students/${id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: form.name,
          class: form.class,
          roll: form.roll,
          gender: form.gender,
          dob: form.dob,
          house: form.house,
          bloodGroup: form.bloodGroup,
          admissionNo: form.admissionNo,
          riskScore: Number(form.riskScore) || 0,
          riskLevel: form.riskLevel,
          attendance: Number(form.attendance) || 0,
          feesDue: Number(form.feesDue) || 0,
          feesStatus: form.feesStatus,
          gpa: Number(form.gpa) || 0,
          behavior: form.behavior,
          aiSummary: form.aiSummary,
          parent: form.parent,
          medical: form.medical,
          recommendations: form.recommendations,
          achievements: form.achievements,
          timeline: form.timeline,
          marks: form.marks,
        }),
      })
      setDetail(updated)
      setEditing(false)
      toast('Student updated', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const saveMarks = async () => {
    setSavingMarks(true)
    try {
      const updated = await api(`/api/students/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ marks: draftMarks }),
      })
      setDetail(updated)
      setMarksOpen(false)
      toast('Marks saved — trends updated', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setSavingMarks(false)
    }
  }

  const saveFees = async () => {
    setFeeSaving(true)
    try {
      const updated = await api(`/api/students/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ feesDue: Number(draftFees.feesDue) || 0, feesStatus: draftFees.feesStatus }),
      })
      setDetail(updated)
      setFeesOpen(false)
      toast('Fees updated', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setFeeSaving(false)
    }
  }

  const recordPayment = async () => {
    const amount = Number(payment.amount)
    if (!amount || amount <= 0) { toast('Enter a payment amount', 'warning'); return }
    const date = payment.date || new Date().toISOString().slice(0, 10)
    setPaySaving(true)
    try {
      const remaining = Math.max(0, (Number(s.feesDue) || 0) - amount)
      const timeline = [
        { id: Date.now(), date, type: 'fees', title: `Payment recorded ₹${amount.toLocaleString()}`, detail: `Fee payment · balance ₹${remaining.toLocaleString()}` },
        ...(s.timeline || []),
      ]
      const updated = await api(`/api/students/${id}`, {
        method: 'PUT',
        body: JSON.stringify({ feesDue: remaining, feesStatus: remaining > 0 ? (draftFees.feesStatus === 'Cleared' ? 'Partial' : draftFees.feesStatus) : 'Cleared', timeline }),
      })
      setDetail(updated)
      setPayment({ amount: '', date: '' })
      setPayOpen(false)
      toast(`Payment of ₹${amount.toLocaleString()} recorded`, 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setPaySaving(false)
    }
  }

  const removeStudent = async () => {
    if (!confirm(`Delete ${s.name} permanently? This cannot be undone.`)) return
    try {
      await api(`/api/students/${id}`, { method: 'DELETE' })
      toast(`${s.name} removed`, 'info')
      navigate('/students')
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  if (!s && !notFound) {
    return <div className="py-20 text-center text-slate-400">Loading student…</div>
  }

  if (notFound || !s) {
    return (
      <div className="py-20 text-center">
        <p className="text-slate-600">Student not found</p>
        <Button className="mt-4" onClick={() => navigate('/students')}>
          Back
        </Button>
      </div>
    )
  }

  const timeline = s.timeline || []
  const docs = s.documents || []
  const recommendations = s.recommendations || []
  const achievements = s.achievements || []
  const medical = s.medical || {}
  const behavior = s.behavior || ''

  return (
    <>
      <div className="mx-auto max-w-7xl space-y-6">
      <button
        type="button"
        onClick={() => navigate('/students')}
        className="inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:underline"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Students
      </button>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex gap-4">
          <div
            className={`flex h-16 w-16 items-center justify-center rounded-2xl text-lg font-bold text-white shadow-lg ${
              s.riskLevel === 'High'
                ? 'bg-gradient-to-br from-red-500 to-red-800'
                : 'bg-gradient-to-br from-navy-600 to-navy-950'
            }`}
          >
            {s.photo}
          </div>
          <div>
            <PageHeader
              className="!mb-0"
              eyebrow="Student 360"
              title={s.name}
              subtitle={`${s.class} · ${s.admissionNo} · House ${s.house} · DOB ${s.dob}`}
            />
            <div className="mt-2 flex flex-wrap gap-2">
              <StatusBadge status={s.riskLevel === 'High' ? 'Missing' : s.riskLevel === 'Medium' ? 'Expiring' : 'Current'} />
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
                Risk score {s.riskScore}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
                GPA {s.gpa}
              </span>
              <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600">
                Attendance {s.attendance}%
              </span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              toast(`Calling ${s.parent.phone}…`, 'info')
            }}
          >
            <Phone className="h-3.5 w-3.5" /> Call parent
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
            <Pencil className="h-3.5 w-3.5" /> Edit
          </Button>
          <Button size="sm" variant="dangerOutline" onClick={removeStudent}>
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => {
              dispatch({
                type: 'ADD_MEETING',
                payload: {
                  id: Date.now(),
                  title: `Parent conference – ${s.name}`,
                  date: '2025-07-30',
                  time: '3:00 PM',
                  attendees: [user?.name || 'You', s.parent.name],
                  status: 'Upcoming',
                  agenda: 'Risk review & support plan',
                },
              })
              toast('Conference scheduled', 'success')
              navigate('/calendar')
            }}
          >
            <CalendarPlus className="h-3.5 w-3.5" /> Schedule
          </Button>
          <Button
            size="sm"
            onClick={() =>
              navigate('/ai/chat', {
                state: { seedQuestion: `Create intervention plan for ${s.name} (${s.class})` },
              })
            }
          >
            <Sparkles className="h-3.5 w-3.5" /> Success AI
          </Button>
        </div>
      </div>

      <InsightBanner title="AI Summary" items={[s.aiSummary, ...s.recommendations]} />

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`shrink-0 border-b-2 px-4 py-2.5 text-sm font-medium transition ${
              tab === t
                ? 'border-navy-900 text-navy-900'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'Overview' && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <Section title="Performance snapshot">
              <div className="grid grid-cols-3 gap-3">
                <Metric label="Attendance" value={`${s.attendance}%`} />
                <Metric label="GPA" value={String(s.gpa)} />
                <Metric label="Fees" value={s.feesStatus} />
              </div>
              <p className="mt-4 text-sm text-slate-600">
                <strong>Behavior:</strong> {s.behavior}
              </p>
              {s.achievements.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-slate-500">Achievements</p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {s.achievements.map((a) => (
                      <li key={a}>{a}</li>
                    ))}
                  </ul>
                </div>
              )}
            </Section>
            <Section title="Recent timeline" padding={false}>
              <Timeline items={timeline.slice(0, 5)} />
              <div className="border-t border-slate-50 px-5 py-3">
                <button type="button" className="text-xs font-medium text-navy-600" onClick={() => setTab('Timeline')}>
                  Full AI Student Timeline →
                </button>
              </div>
            </Section>
          </div>
          <div className="space-y-4">
            <Section title="Parent / Guardian">
              <p className="font-semibold text-slate-900">{s.parent.name}</p>
              <p className="text-xs text-slate-500">{s.parent.relation}</p>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <p className="flex items-center gap-2">
                  <Phone className="h-3.5 w-3.5" /> {s.parent.phone}
                </p>
                <p className="flex items-center gap-2">
                  <Mail className="h-3.5 w-3.5" /> {s.parent.email}
                </p>
              </div>
            </Section>
            <Section title="AI recommendations">
              <ul className="space-y-2">
                {s.recommendations.map((r) => (
                  <li key={r}>
                    <button
                      type="button"
                      onClick={() => toast(`Action queued: ${r}`, 'success')}
                      className="w-full rounded-xl border border-slate-100 px-3 py-2.5 text-left text-xs font-medium text-slate-700 hover:border-navy-200 hover:bg-navy-50"
                    >
                      {r}
                    </button>
                  </li>
                ))}
              </ul>
            </Section>
          </div>
        </div>
      )}

      {tab === 'Timeline' && (
        <Section title="AI Student Timeline" subtitle="Institutional memory for this learner">
          <Timeline items={timeline} />
        </Section>
      )}

      {tab === 'Documents' && (
        <Section
          title="Student Document Vault"
          subtitle="Secure retrieval — AI can surface these instantly"
          action={
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" onClick={syncVault} disabled={syncing}>
                <RefreshCw className="h-3.5 w-3.5 mr-1" /> Sync vault
              </Button>
              <Button size="sm" variant="secondary" onClick={() => fileInputRef.current?.click()}>
                Upload
              </Button>
            </div>
          }
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              const form = new FormData()
              form.append('file', file)
              try {
                await api(`/api/students/${id}/documents/upload`, { method: 'POST', body: form })
                toast(`${file.name} uploaded`, 'success')
                const d = await api(`/api/students/${id}/documents`)
                setDocuments(Object.values(d.documents || {}))
              } catch {
                toast('Upload failed', 'error')
              }
              e.target.value = ''
            }}
          />
          {docsLoading ? (
            <div className="py-6 text-center text-slate-400 text-sm">Loading documents…</div>
          ) : documents.length === 0 ? (
            <div className="py-6 text-center text-slate-400 text-sm">No documents uploaded yet</div>
          ) : (
            <ul className="space-y-2">
              {documents.map((d) => (
                <li
                  key={d.file_id}
                  className="flex items-center justify-between rounded-xl border border-slate-100 px-4 py-3"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="h-4 w-4 text-navy-500" />
                    <div>
                      <p className="text-sm font-medium text-slate-800">{d.name}</p>
                      <p className="text-[11px] text-slate-400">
                        {d.student_id || 'Student'} · Updated {new Date(d.uploaded_at * 1000).toISOString().slice(0, 10)}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        window.open(`/api/students/${id}/documents/${d.file_id}/download`, '_blank')
                      }}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={async () => {
                        try {
                          await api(`/api/students/${id}/documents/${d.file_id}`, { method: 'DELETE' })
                          toast(`Deleted ${d.name}`, 'success')
                          const updated = await api(`/api/students/${id}/documents`)
                          setDocuments(Object.values(updated.documents || {}))
                        } catch {
                          toast('Delete failed', 'error')
                        }
                      }}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 text-slate-400"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {tab === 'Academics' && (
        <Section title="Academic profile">
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm text-slate-600">
              GPA <strong>{s.gpa}</strong> · Class {s.class}. Arrows compare the latest two exam periods per subject.
            </p>
            <Button size="sm" variant="secondary" onClick={() => { setMarksOpen(!marksOpen); setDraftMarks(JSON.parse(JSON.stringify(s.marks || []))) }}>
              <Pencil className="h-3.5 w-3.5" /> Edit marks
            </Button>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            {(s.subjectTrends && s.subjectTrends.length
              ? s.subjectTrends
              : [
                  { subject: 'Math', trend: '↓' },
                  { subject: 'Science', trend: '→' },
                  { subject: 'Languages', trend: '↑' },
                ]
            ).map((t) => (
              <Metric key={t.subject} label={`${t.subject} trend`} value={t.trend} />
            ))}
          </div>

          {marksOpen && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
              <p className="mb-2 text-xs font-medium text-slate-500">Subject marks — one row per subject per exam period. Arrows update from the latest two.</p>
              <div className="space-y-2">
                {draftMarks.map((m, i) => (
                  <div key={i} className="grid items-center gap-2 rounded-lg border border-slate-100 bg-white p-2 md:grid-cols-[minmax(0,1fr)_130px_90px_140px_auto]">
                    <input className="field" value={m.subject} onChange={(e) => setDraftMarks((prev) => { const c = [...prev]; c[i] = { ...c[i], subject: e.target.value }; return c })} placeholder="Subject" />
                    <input className="field m-0 w-full" value={m.period} onChange={(e) => setDraftMarks((prev) => { const c = [...prev]; c[i] = { ...c[i], period: e.target.value }; return c })} placeholder="Period" />
                    <input className="field m-0 w-full" type="number" value={m.mark ?? ''} onChange={(e) => setDraftMarks((prev) => { const c = [...prev]; c[i] = { ...c[i], mark: Number(e.target.value) }; return c })} placeholder="Mark" />
                    <input className="field m-0 w-full" type="date" value={m.date ?? ''} onChange={(e) => setDraftMarks((prev) => { const c = [...prev]; c[i] = { ...c[i], date: e.target.value }; return c })} placeholder="Date" />
                    <button type="button" onClick={() => setDraftMarks((prev) => prev.filter((_, j) => j !== i))} className="text-slate-400 hover:text-danger-500" title="Remove">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Button size="sm" variant="secondary" onClick={() => setDraftMarks((prev) => [...prev, { subject: '', period: '', mark: '', date: '' }])}>
                  <Plus className="h-3.5 w-3.5" /> Add row
                </Button>
                <div className="flex-1" />
                <Button size="sm" variant="secondary" onClick={() => setMarksOpen(false)}>Cancel</Button>
                <Button size="sm" onClick={saveMarks} disabled={savingMarks}>{savingMarks ? 'Saving…' : 'Save marks'}</Button>
              </div>
            </div>
          )}
        </Section>
      )}

      {tab === 'Fees' && (
        <Section title="Fee intelligence">
          <div className="flex items-center justify-between gap-3">
            <div className="grid flex-1 gap-3 sm:grid-cols-3">
              <Metric label="Status" value={s.feesStatus} />
              <Metric label="Due" value={s.feesDue ? `₹${s.feesDue.toLocaleString()}` : '₹0'} />
              <Metric label="Risk link" value={s.feesDue ? 'Elevated' : 'None'} />
            </div>
            <Button size="sm" variant="secondary" onClick={() => { setFeesOpen(!feesOpen); setDraftFees({ feesDue: s.feesDue, feesStatus: s.feesStatus }) }}>
              <Pencil className="h-3.5 w-3.5" /> Edit fees
            </Button>
          </div>

          {feesOpen && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50/60 p-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Amount due (₹)</label>
                  <input type="number" className="field m-0 w-full" value={draftFees.feesDue} onChange={(e) => setDraftFees((f) => ({ ...f, feesDue: Number(e.target.value) }))} />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Status</label>
                  <select className="field m-0 w-full" value={draftFees.feesStatus} onChange={(e) => setDraftFees((f) => ({ ...f, feesStatus: e.target.value }))}>
                    {['Cleared', 'Partial', 'Overdue', 'Pending'].map((st) => <option key={st}>{st}</option>)}
                  </select>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <div className="flex-1" />
                <Button size="sm" variant="secondary" onClick={() => setFeesOpen(false)}>Cancel</Button>
                <Button size="sm" onClick={saveFees} disabled={feeSaving}>{feeSaving ? 'Saving…' : 'Save fees'}</Button>
              </div>
            </div>
          )}

          {payOpen && (
            <div className="mt-4 rounded-xl border border-slate-200 bg-white p-4">
              <p className="mb-2 text-xs font-medium text-slate-500">Record a fee payment</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-500">Amount (₹)</label>
                <input type="number" className="field m-0 w-full" value={payment.amount} onChange={(e) => setPayment((p) => ({ ...p, amount: e.target.value }))} placeholder="e.g. 15000" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-500">Recovered on</label>
                <input type="date" className="field m-0 w-full" value={payment.date} onChange={(e) => setPayment((p) => ({ ...p, date: e.target.value }))} />
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1" />
              <Button size="sm" onClick={recordPayment} disabled={paySaving}>{paySaving ? 'Saving…' : 'Record payment'}</Button>
            </div>
          </div>
          )}

          <div className="mt-4 flex items-center gap-2">
            {!payOpen && (
              <Button size="sm" variant="secondary" onClick={() => setPayOpen(true)}>
                <Plus className="h-3.5 w-3.5" /> Record payment
              </Button>
            )}
            <Button className="ml-auto" size="sm" onClick={() => navigate('/finance')}>
              Open Finance Intelligence
            </Button>
          </div>
        </Section>
      )}

      {tab === 'Medical' && (
        <Section title="Medical">
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-xs text-slate-400">Blood group</dt>
              <dd className="font-medium">{s.bloodGroup}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Allergies</dt>
              <dd className="font-medium">{s.medical.allergies}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-400">Conditions</dt>
              <dd className="font-medium">{s.medical.conditions}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-slate-400">Last checkup {s.medical.lastCheckup}</p>
        </Section>
      )}

      {tab === 'Communication' && (
        <Section title="Communication history">
          {composing ? (
            <form onSubmit={async (e) => {
              e.preventDefault()
              if (!msg.subject.trim()) return
              try {
                await api(`/api/students/${id}/communications`, {
                  method: 'POST',
                  body: JSON.stringify(msg),
                })
                setMsg({ channel: 'call', subject: '', body: '' })
                setComposing(false)
                const d = await api(`/api/students/${id}/communications`)
                setCommunications(d.communications || [])
                toast('Message logged', 'success')
              } catch {
                toast('Failed to send', 'error')
              }
            }} className="space-y-2 rounded-xl border border-slate-200 bg-white p-4">
              <select className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={msg.channel} onChange={(e) => setMsg({ ...msg, channel: e.target.value })}>
                <option value="call">Call</option><option value="sms">SMS</option><option value="email">Email</option><option value="meeting">Meeting</option>
              </select>
              <input required placeholder="Subject" className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={msg.subject} onChange={(e) => setMsg({ ...msg, subject: e.target.value })} />
              <textarea required rows={3} placeholder="Write a note…" className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={msg.body} onChange={(e) => setMsg({ ...msg, body: e.target.value })} />
              <div className="flex gap-2">
                <Button size="sm" type="submit">Send</Button>
                <Button size="sm" variant="ghost" type="button" onClick={() => setComposing(false)}>Cancel</Button>
              </div>
            </form>
          ) : (
            <>
              <ul className="space-y-3 text-sm text-slate-600">
                {communications.map((c) => (
                  <li key={c.id} className="rounded-xl border border-slate-100 p-3">
                    <p className="font-medium text-slate-800">{c.subject}</p>
                    <p className="text-xs text-slate-400">{c.channel} · {c.author}</p>
                    {c.body && <p className="mt-1 text-xs text-slate-500">{c.body}</p>}
                  </li>
                ))}
              </ul>
              <Button className="mt-4" size="sm" variant="secondary" onClick={() => setComposing(true)}>
                <MessageSquare className="h-4 w-4" /> New message
              </Button>
            </>
          )}
        </Section>
      )}

      </div>

      {form && editing && (
        <Modal
          open={editing}
          onClose={() => setEditing(false)}
          title={`Edit ${form.name}`}
          size="xl"
          footer={
            <>
              <Button variant="ghost" onClick={() => setEditing(false)}>Cancel</Button>
              <Button onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</Button>
            </>
          }
        >
          <div className="space-y-5">
            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Name"><input className="field" value={form.name} onChange={(e) => setF('name', e.target.value)} /></Field>
              <Field label="Class"><input className="field" value={form.class} onChange={(e) => setF('class', e.target.value)} /></Field>
              <Field label="Roll"><input className="field" value={form.roll} onChange={(e) => setF('roll', e.target.value)} /></Field>
              <Field label="Admission no."><input className="field" value={form.admissionNo} onChange={(e) => setF('admissionNo', e.target.value)} /></Field>
              <Field label="House"><input className="field" value={form.house} onChange={(e) => setF('house', e.target.value)} /></Field>
              <Field label="DOB"><input className="field" value={form.dob} onChange={(e) => setF('dob', e.target.value)} /></Field>
              <Field label="Gender"><input className="field" value={form.gender} onChange={(e) => setF('gender', e.target.value)} /></Field>
              <Field label="Blood group"><input className="field" value={form.bloodGroup} onChange={(e) => setF('bloodGroup', e.target.value)} /></Field>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Risk score"><input type="number" className="field" value={form.riskScore} onChange={(e) => setF('riskScore', e.target.value)} /></Field>
              <Field label="Risk level">
                <select className="field" value={form.riskLevel} onChange={(e) => setF('riskLevel', e.target.value)}>
                  <option>Low</option><option>Medium</option><option>High</option>
                </select>
              </Field>
              <Field label="Attendance %"><input type="number" className="field" value={form.attendance} onChange={(e) => setF('attendance', e.target.value)} /></Field>
              <Field label="GPA"><input type="number" step="0.1" className="field" value={form.gpa} onChange={(e) => setF('gpa', e.target.value)} /></Field>
              <Field label="Fees due (₹)"><input type="number" className="field" value={form.feesDue} onChange={(e) => setF('feesDue', e.target.value)} /></Field>
              <Field label="Fees status">
                <select className="field" value={form.feesStatus} onChange={(e) => setF('feesStatus', e.target.value)}>
                  <option>Cleared</option><option>Partial</option><option>Overdue</option>
                </select>
              </Field>
            </div>

            <Field label="AI summary"><textarea rows={3} className="field" value={form.aiSummary} onChange={(e) => setF('aiSummary', e.target.value)} /></Field>
            <Field label="Behavior"><input className="field" value={form.behavior} onChange={(e) => setF('behavior', e.target.value)} /></Field>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Parent name"><input className="field" value={form.parent.name} onChange={(e) => setParent('name', e.target.value)} /></Field>
              <Field label="Relation"><input className="field" value={form.parent.relation} onChange={(e) => setParent('relation', e.target.value)} /></Field>
              <Field label="Phone"><input className="field" value={form.parent.phone} onChange={(e) => setParent('phone', e.target.value)} /></Field>
              <Field label="Email"><input className="field" value={form.parent.email} onChange={(e) => setParent('email', e.target.value)} /></Field>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <Field label="Allergies"><input className="field" value={form.medical.allergies} onChange={(e) => setMedical('allergies', e.target.value)} /></Field>
              <Field label="Conditions"><input className="field" value={form.medical.conditions} onChange={(e) => setMedical('conditions', e.target.value)} /></Field>
              <Field label="Last checkup"><input className="field" value={form.medical.lastCheckup} onChange={(e) => setMedical('lastCheckup', e.target.value)} /></Field>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <ListEditor
                label="Recommendations"
                items={form.recommendations}
                setItems={(v) => setF('recommendations', v)}
              />
              <ListEditor
                label="Achievements"
                items={form.achievements}
                setItems={(v) => setF('achievements', v)}
              />
            </div>

            <div>
              <p className="mb-1.5 text-xs font-medium text-slate-500">Timeline</p>
              <div className="space-y-2">
                {form.timeline.map((t, i) => (
                  <div key={i} className="grid gap-2 rounded-lg border border-slate-100 p-2 sm:grid-cols-[110px_120px_1fr_150px_auto]">
                    <input className="field" value={t.date} onChange={(e) => {
                      const timeline = [...form.timeline]
                      timeline[i] = { ...t, date: e.target.value }
                      setF('timeline', timeline)
                    }} placeholder="Date" />
                    <select className="field" value={t.type} onChange={(e) => {
                      const timeline = [...form.timeline]
                      timeline[i] = { ...t, type: e.target.value }
                      setF('timeline', timeline)
                    }}>
                      {['attendance', 'fees', 'academic', 'meeting', 'document', 'achievement', 'admission'].map((ty) => <option key={ty}>{ty}</option>)}
                    </select>
                    <input className="field" value={t.title} onChange={(e) => {
                      const timeline = [...form.timeline]
                      timeline[i] = { ...t, title: e.target.value }
                      setF('timeline', timeline)
                    }} placeholder="Title" />
                    <input className="field" value={t.detail} onChange={(e) => {
                      const timeline = [...form.timeline]
                      timeline[i] = { ...t, detail: e.target.value }
                      setF('timeline', timeline)
                    }} placeholder="Detail" />
                    <button type="button" onClick={() => setF('timeline', form.timeline.filter((_, j) => j !== i))} className="text-slate-400 hover:text-danger-500" title="Remove">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
                <Button size="sm" variant="secondary" onClick={() => setF('timeline', [...form.timeline, { id: Date.now(), date: '', type: 'attendance', title: '', detail: '' }])}>
                  <Plus className="h-3.5 w-3.5" /> Add event
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-slate-500">{label}</label>
      {children}
    </div>
  )
}

function ListEditor({ label, items, setItems }) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-slate-500">{label}</p>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex gap-2">
            <input
              className="field flex-1"
              value={item}
              onChange={(e) => {
                const next = [...items]
                next[i] = e.target.value
                setItems(next)
              }}
            />
            <button
              type="button"
              onClick={() => setItems(items.filter((_, j) => j !== i))}
              className="text-slate-400 hover:text-danger-500"
              title="Remove"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        <Button size="sm" variant="secondary" onClick={() => setItems([...items, ''])}>
          <Plus className="h-3.5 w-3.5" /> Add
        </Button>
      </div>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-50 px-3 py-3">
      <p className="text-[11px] text-slate-400">{label}</p>
      <p className="mt-0.5 text-lg font-bold text-slate-900">{value}</p>
    </div>
  )
}

function Timeline({ items }) {
  const colors = {
    attendance: 'bg-amber-500',
    fees: 'bg-orange-500',
    academic: 'bg-navy-600',
    meeting: 'bg-violet-500',
    document: 'bg-sky-500',
    achievement: 'bg-emerald-500',
    admission: 'bg-slate-500',
  }
  return (
    <ul className="relative space-y-0 px-5 py-2">
      {items.map((item, i) => (
        <li key={item.id} className="relative flex gap-4 pb-6 last:pb-2">
          {i < items.length - 1 && (
            <span className="absolute left-[7px] top-3 h-full w-px bg-slate-200" />
          )}
          <span className={`relative z-10 mt-1.5 h-3.5 w-3.5 shrink-0 rounded-full ${colors[item.type] || 'bg-navy-500'}`} />
          <div>
            <p className="text-[11px] font-medium text-slate-400">{item.date}</p>
            <p className="text-sm font-semibold text-slate-800">{item.title}</p>
            <p className="text-xs text-slate-500">{item.detail}</p>
          </div>
        </li>
      ))}
    </ul>
  )
}
