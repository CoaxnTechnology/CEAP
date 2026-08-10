import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FilePenLine,
  Check,
  AlertCircle,
  Edit3,
  ThumbsUp,
  ThumbsDown,
  FileText,
  Sparkles,
  RotateCcw,
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const generateSteps = [
  { id: 1, label: 'Select Type' },
  { id: 2, label: 'Choose Template' },
  { id: 3, label: 'AI Draft' },
  { id: 4, label: 'Human Review' },
  { id: 5, label: 'Publish' },
]

const departments = ['Academic', 'HR', 'Finance', 'Admin', 'Transport', 'IT', 'Sports']
const academicYears = ['2024-25', '2025-26', '2023-24']

const agentDeptMap = {
  principal: 'Admin',
  teacher: 'Academic',
  finance: 'Finance',
  admissions: 'Admin',
  hr: 'HR',
  compliance: 'Admin',
  library: 'Admin',
  success: 'Academic',
}

export default function Generate() {
  const { dispatch, toast, user, activeAgent } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [docType, setDocType] = useState('Circular')
  const [template, setTemplate] = useState('')
  const [year, setYear] = useState('2025-26')
  const [department, setDepartment] = useState(activeAgent ? (agentDeptMap[activeAgent.id] || 'Admin') : 'Admin')
  const [audience, setAudience] = useState('Parents')
  const [topic, setTopic] = useState('Annual Day 2025')
  const [draft, setDraft] = useState('')
  const [title, setTitle] = useState('')
  const [status, setStatus] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [confirmPublish, setConfirmPublish] = useState(false)
  const [templates, setTemplates] = useState({})
  const [templatesLoaded, setTemplatesLoaded] = useState(false)
  const [sources, setSources] = useState([])

  useEffect(() => {
    api('/api/ai/templates')
      .then((data) => {
        setTemplates(data)
        setTemplatesLoaded(true)
        const first = Object.values(data)[0]?.[0]
        if (first) setTemplate(first.id)
      })
      .catch(() => {
        toast('Failed to load templates', 'error')
        setTemplatesLoaded(true)
      })
  }, [])

  useEffect(() => {
    if (templatesLoaded) {
      const first = templates[docType]?.[0]
      if (first) setTemplate(first.id)
    }
  }, [docType, templatesLoaded])

  const templatesForType = templates[docType] || []

  function renderDraftWithCitations(text) {
    const parts = text.split(/(\[\[cite:\d+\]\])/g)
    return parts.map((part, i) => {
      const match = part.match(/\[\[cite:(\d+)\]\]/)
      if (match) {
        return (
          <button
            key={i}
            type="button"
            className="citation-mark"
            title={`Source ${match[1]}`}
            onClick={() => toast(`Citation source [${match[1]}] highlighted`, 'info')}
          >
            [{match[1]}]
          </button>
        )
      }
      return <span key={i}>{part}</span>
    })
  }

  function goToStep(id) {
    if (id <= step || (id === step + 1 && canAdvance())) {
      setStep(id)
    } else if (id < step) {
      setStep(id)
    } else {
      toast('Complete the current step first', 'warning')
    }
  }

  function canAdvance() {
    if (step === 1) return !!docType
    if (step === 2) return !!template
    if (step === 3) return !!draft
    return true
  }

  async function generateDraft() {
    setGenerating(true)
    try {
      const result = await api('/api/ai/generate', {
        method: 'POST',
        body: JSON.stringify({
          doc_type: docType,
          template_id: template,
          topic,
          department,
          audience,
          academic_year: year,
          agent_scope: activeAgent ? `${activeAgent.name}: ${activeAgent.scope}` : undefined,
        }),
      })
      setTitle(result.title)
      setDraft(result.content)
      setSources(result.sources || [])
      setStep(3)
      setStatus(null)
      toast('AI draft generated — ready for human review', 'success')
      dispatch({
        type: 'ADD_ACTIVITY',
        payload: {
          id: Date.now(),
          user: user?.name || 'User',
          action: 'Generated',
          target: result.title,
          time: 'Just now',
          type: 'generate',
        },
      })
    } catch (err) {
      toast(err.message || 'Generation failed', 'error')
    } finally {
      setGenerating(false)
    }
  }

  function handleApprove() {
    setConfirmPublish(false)
    setStatus('approved')
    setStep(5)
    dispatch({
      type: 'PUBLISH_DOCUMENT',
      payload: {
        title,
        type: docType,
        department,
        year,
        content: draft,
        citation: `${docType.slice(0, 3).toUpperCase()}-${Date.now().toString().slice(-6)}`,
        audience,
      },
    })
    toast('Document approved and published to Knowledge Library', 'success')
  }

  function handleReject() {
    setStatus('rejected')
    setStep(4)
    toast('Draft rejected — edit and resubmit for approval', 'warning')
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-navy-500">
          AI Workspace · Document Studio
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">AI Document Studio</h1>
        <p className="mt-1 text-sm text-slate-500">
          Circulars, letters, certificates, minutes, policies — AI drafts, humans approve. AI never publishes alone.
        </p>
      </div>

      <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
        <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div>
          <p className="text-sm font-semibold text-amber-900">AI never publishes — Human approval required</p>
          <p className="mt-0.5 text-xs text-amber-800/80">
            Every document stays in draft until an authorized reviewer approves and publishes it.
          </p>
        </div>
      </div>

      <Card className="!py-4">
        <ol className="flex flex-wrap items-center justify-between gap-2">
          {generateSteps.map((s, idx) => {
            const done = step > s.id || (s.id === 5 && status === 'approved')
            const active = step === s.id
            return (
              <li key={s.id} className="flex min-w-[100px] flex-1 items-center gap-2">
                <button type="button" onClick={() => goToStep(s.id)} className="flex items-center gap-2">
                  <span
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                      done
                        ? 'bg-success-500 text-white'
                        : active
                          ? 'bg-navy-900 text-white'
                          : 'bg-slate-100 text-slate-400'
                    }`}
                  >
                    {done ? <Check className="h-4 w-4" /> : s.id}
                  </span>
                  <span
                    className={`hidden text-xs font-medium sm:inline ${
                      active ? 'text-navy-900' : done ? 'text-success-700' : 'text-slate-400'
                    }`}
                  >
                    {s.label}
                  </span>
                </button>
                {idx < generateSteps.length - 1 && (
                  <div
                    className={`mx-1 hidden h-px flex-1 sm:block ${
                      step > s.id ? 'bg-success-400' : 'bg-slate-200'
                    }`}
                  />
                )}
              </li>
            )
          })}
        </ol>
      </Card>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-8">
          <Card>
            <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FilePenLine className="h-4 w-4 text-navy-600" />
              Document settings
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Document Type">
                <select
                  value={docType}
                  onChange={(e) => {
                    setDocType(e.target.value)
                    if (step < 2) setStep(1)
                  }}
                  className="field-input"
                >
                  {Object.keys(templates).map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Template">
                <select
                  value={template}
                  onChange={(e) => {
                    setTemplate(e.target.value)
                    if (step < 2) setStep(2)
                  }}
                  className="field-input"
                >
                  {templatesForType.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Topic / Subject" className="sm:col-span-2">
                <input
                  className="field-input"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Annual Day 2025"
                />
              </Field>
              <Field label="Academic Year">
                <select value={year} onChange={(e) => setYear(e.target.value)} className="field-input">
                  {academicYears.map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Department">
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="field-input"
                >
                  {departments.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Audience" className="sm:col-span-2">
                <select
                  value={audience}
                  onChange={(e) => setAudience(e.target.value)}
                  className="field-input"
                >
                  <option>Parents</option>
                  <option>Staff</option>
                  <option>Students</option>
                  <option>Board / Inspectors</option>
                  <option>All stakeholders</option>
                </select>
              </Field>
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {step <= 2 && (
                <Button onClick={() => setStep(2)} variant="secondary">
                  Confirm template
                </Button>
              )}
              <Button onClick={generateDraft} disabled={generating || !templatesLoaded}>
                <Sparkles className="h-4 w-4" />
                {generating ? 'Generating\u2026' : step >= 3 ? 'Regenerate AI Draft' : 'Generate AI Draft'}
              </Button>
            </div>
          </Card>

          {(step >= 3 || status) && (
            <Card padding={false}>
              <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
                <div>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full border-0 bg-transparent text-sm font-semibold text-slate-900 outline-none"
                  />
                  <p className="text-[11px] text-slate-400">
                    {status === 'approved'
                      ? 'Published'
                      : step >= 4
                        ? 'Human review mode \u2014 editable'
                        : 'AI draft \u00b7 Citations clickable \u00b7 Review required'}
                  </p>
                </div>
                {status === 'approved' && (
                  <span className="rounded-full bg-success-50 px-2.5 py-1 text-xs font-semibold text-success-700">
                    Approved
                  </span>
                )}
                {status === 'rejected' && (
                  <span className="rounded-full bg-danger-50 px-2.5 py-1 text-xs font-semibold text-danger-600">
                    Rejected
                  </span>
                )}
              </div>
              <div className="max-h-[480px] overflow-y-auto px-5 py-4">
                {step >= 4 && status !== 'approved' ? (
                  <textarea
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    className="min-h-[400px] w-full resize-y rounded-lg border border-slate-200 bg-slate-50 p-4 font-mono text-sm leading-relaxed text-slate-700 outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100"
                  />
                ) : (
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-700">
                    {renderDraftWithCitations(draft)}
                  </pre>
                )}
              </div>
            </Card>
          )}
        </div>

        <aside className="space-y-4 lg:col-span-4">
          <Card>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FileText className="h-4 w-4 text-navy-600" />
              Sources Used
            </h3>
            <p className="mt-1 text-[11px] text-slate-400">Documents cited in this draft</p>
            <ul className="mt-3 space-y-2">
              {sources.length === 0 && (
                <li className="text-xs text-slate-400">No sources yet</li>
              )}
              {sources.map((s, i) => (
                <li key={s.file_id || i}>
                  <button
                    type="button"
                    onClick={() => toast(`Viewing ${s.name || s.source}`, 'info')}
                    className="w-full rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-left hover:border-navy-200"
                  >
                    <p className="text-xs font-semibold text-slate-800">{s.name || s.source}</p>
                    <p className="text-[10px] text-navy-600">{s.source}</p>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <Card className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Review actions
            </p>
            <Button
              className="w-full"
              variant="secondary"
              disabled={step < 3}
              onClick={() => {
                setStep(4)
                setStatus(null)
                toast('Edit mode enabled', 'info')
              }}
            >
              <Edit3 className="h-4 w-4" />
              Edit
            </Button>
            <Button
              className="w-full"
              variant="success"
              disabled={step < 3 || status === 'approved'}
              onClick={() => setConfirmPublish(true)}
            >
              <ThumbsUp className="h-4 w-4" />
              Approve & Publish
            </Button>
            <Button
              className="w-full"
              variant="dangerOutline"
              disabled={step < 3 || status === 'approved'}
              onClick={handleReject}
            >
              <ThumbsDown className="h-4 w-4" />
              Reject
            </Button>
            {status === 'approved' && (
              <div className="space-y-2 pt-2">
                <p className="text-center text-xs font-medium text-success-700">
                  Document published to Knowledge Library
                </p>
                <Button className="w-full" variant="secondary" onClick={() => navigate('/library')}>
                  View in Library
                </Button>
                <Button
                  className="w-full"
                  variant="ghost"
                  onClick={() => {
                    setStep(1)
                    setStatus(null)
                    setTopic('')
                    toast('Started new document', 'info')
                  }}
                >
                  <RotateCcw className="h-4 w-4" /> New document
                </Button>
              </div>
            )}
            {status === 'rejected' && (
              <p className="pt-2 text-center text-xs font-medium text-danger-600">
                Draft returned for revision \u2014 edit and approve again
              </p>
            )}
          </Card>

          <Card className="border-navy-100 bg-navy-50">
            <p className="text-xs font-semibold text-navy-800">Workflow</p>
            <p className="mt-1 text-[11px] leading-relaxed text-navy-700/80">
              Select Type \u2192 Choose Template \u2192 AI Draft \u2192 Human Review \u2192 Publish. Only authorized
              roles can complete the final publish step.
            </p>
          </Card>
        </aside>
      </div>

      <Modal
        open={confirmPublish}
        onClose={() => setConfirmPublish(false)}
        title="Confirm publish"
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmPublish(false)}>
              Cancel
            </Button>
            <Button variant="success" onClick={handleApprove}>
              <ThumbsUp className="h-4 w-4" /> Confirm Approve & Publish
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-600">
          You are about to publish <strong>{title}</strong> to the Knowledge Library. This action
          is attributed to <strong>{user?.name}</strong> ({user?.role}). AI cannot publish without
          this human confirmation.
        </p>
      </Modal>

      <style>{`
        .field-input {
          width: 100%;
          border-radius: 0.5rem;
          border: 1px solid #e2e8f0;
          background: #f8fafc;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
          color: #1e293b;
          outline: none;
        }
        .field-input:focus {
          border-color: #627d98;
          background: white;
          box-shadow: 0 0 0 2px #d9e2ec;
        }
      `}</style>
    </div>
  )
}

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <label className="mb-1.5 block text-xs font-medium text-slate-500">{label}</label>
      {children}
    </div>
  )
}
