import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

export default function Settings() {
  const { preferences, school, darkMode, dispatch, toast, logout } = useApp()
  const navigate = useNavigate()
  const [targets, setTargets] = useState({ revenue_mtd: 5200000, attendance: 90, compliance: 80 })
  const [targetsDirty, setTargetsDirty] = useState(false)
  const [groqKey, setGroqKey] = useState('')
  const [groqModel, setGroqModel] = useState('llama-3.3-70b-versatile')
  const [groqMasked, setGroqMasked] = useState('')
  const [groqConfigured, setGroqConfigured] = useState(false)
  const [groqSaving, setGroqSaving] = useState(false)
  const [showGroqKey, setShowGroqKey] = useState(false)

  useEffect(() => {
    api('/api/settings/targets')
      .then(setTargets)
      .catch(() => {})
  }, [])

  useEffect(() => {
    api('/api/settings/llm')
      .then((d) => {
        setGroqMasked(d.groq_api_key_masked || '')
        setGroqConfigured(!!d.groq_configured)
        setGroqModel(d.groq_model || 'llama-3.3-70b-versatile')
      })
      .catch(() => {})
  }, [])

  async function saveGroq() {
    if (groqKey && !/^gsk_[a-zA-Z0-9]{20,}$/.test(groqKey.trim())) {
      return toast('Invalid Groq key — must start with gsk_', 'error')
    }
    setGroqSaving(true)
    try {
      const body = {}
      if (groqKey.trim()) body.groq_api_key = groqKey.trim()
      if (groqModel.trim()) body.groq_model = groqModel.trim()
      // if user didn't type a new key but we have a masked one, don't send empty key
      if (!groqKey.trim() && groqConfigured) {
        // only model change
        if (!body.groq_model) return toast('Enter a Groq API key or change the model', 'error')
      }
      const res = await api('/api/settings/llm', { method: 'PUT', body: JSON.stringify(body) })
      setGroqMasked(res.groq_api_key_masked || groqMasked)
      setGroqConfigured(!!res.groq_configured)
      setGroqModel(res.groq_model || groqModel)
      setGroqKey('')
      toast('Groq settings saved — new key active immediately', 'success')
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      setGroqSaving(false)
    }
  }

  function setTarget(field, value) {
    const num = value === '' ? '' : Number(value)
    setTargets((t) => ({ ...t, [field]: num }))
    setTargetsDirty(true)
  }

  async function saveTargets() {
    const clean = {}
    for (const [k, v] of Object.entries(targets)) {
      if (v === '' || v === null || Number.isNaN(v)) return toast('Enter valid numbers', 'error')
      clean[k] = Number(v)
    }
    try {
      await api('/api/settings/targets', { method: 'PUT', body: JSON.stringify(clean) })
      setTargetsDirty(false)
      toast('Performance targets saved', 'success')
    } catch (e) {
      toast(e.message, 'error')
    }
  }

  function toggle(key) {
    dispatch({
      type: 'UPDATE_PREFERENCES',
      payload: { [key]: !preferences[key] },
    })
    toast('Preference saved', 'success')
  }

  function updateSchoolField(field, value) {
    dispatch({ type: 'UPDATE_SCHOOL', payload: { [field]: value } })
  }

  function signOut() {
    logout()
    navigate('/login')
    toast('Signed out', 'info')
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Preferences</h1>
        <p className="mt-1 text-sm text-slate-500">Notifications, appearance, and school profile</p>
      </div>

      <Card className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">Notifications</h2>
        <Toggle
          label="Email alerts"
          description="Important compliance and publish events"
          checked={preferences.emailAlerts}
          onChange={() => toggle('emailAlerts')}
        />
        <Toggle
          label="Expiring certificate reminders"
          description="Alert when certificates expire within 30 days"
          checked={preferences.expiringCertReminders}
          onChange={() => toggle('expiringCertReminders')}
        />
        <Toggle
          label="Weekly knowledge digest"
          description="Summary of gaps, activity, and new documents"
          checked={preferences.weeklyDigest}
          onChange={() => toggle('weeklyDigest')}
        />
      </Card>

      <Card className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">Appearance</h2>
        <Toggle
          label="Dark mode"
          description="Toggle application theme"
          checked={darkMode}
          onChange={() => dispatch({ type: 'SET_DARK_MODE', payload: !darkMode })}
        />
      </Card>

      {school && (
        <Card className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">School profile</h2>
          <Field label="School name">
            <input
              className="field"
              value={school.name || ''}
              onChange={(e) => updateSchoolField('name', e.target.value)}
              onBlur={() => toast('School name saved', 'success')}
            />
          </Field>
          <Field label="Board">
            <input
              className="field"
              value={school.board || ''}
              onChange={(e) => updateSchoolField('board', e.target.value)}
              onBlur={() => toast('Board saved', 'success')}
            />
          </Field>
          <Field label="Academic year">
            <input
              className="field"
              value={school.academicYear || ''}
              onChange={(e) => updateSchoolField('academicYear', e.target.value)}
              onBlur={() => toast('Academic year saved', 'success')}
            />
          </Field>
        </Card>
      )}

      <Card className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">Performance targets</h2>
        <p className="text-xs text-slate-400">
          Used by the Executive dashboard and AI briefing to flag below-target metrics.
        </p>
        <Field label="Monthly revenue target (₹)">
          <input
            type="number"
            className="field"
            value={targets.revenue_mtd}
            onChange={(e) => setTarget('revenue_mtd', e.target.value)}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Attendance target (%)">
            <input
              type="number"
              className="field"
              value={targets.attendance}
              onChange={(e) => setTarget('attendance', e.target.value)}
            />
          </Field>
          <Field label="Compliance readiness target (%)">
            <input
              type="number"
              className="field"
              value={targets.compliance}
              onChange={(e) => setTarget('compliance', e.target.value)}
            />
          </Field>
        </div>
        <Button size="sm" onClick={saveTargets} disabled={!targetsDirty}>
          Save targets
        </Button>
      </Card>

      <Card className="space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">AI Provider — Groq</h2>
        <p className="text-xs text-slate-400">
          Groq powers AI Chat, compliance, and executive briefings. Key is stored securely on the server and takes effect immediately — no restart needed.
          {groqConfigured ? (
            <span className="ml-2 inline-flex items-center rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">Configured: {groqMasked}</span>
          ) : (
            <span className="ml-2 inline-flex items-center rounded bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">Not configured</span>
          )}
        </p>
        <Field label="Groq API Key (gsk_...)">
          <div className="flex gap-2">
            <input
              type={showGroqKey ? 'text' : 'password'}
              className="field flex-1"
              placeholder={groqMasked ? `Current: ${groqMasked} — enter new to replace` : 'gsk_...'}
              value={groqKey}
              onChange={(e) => setGroqKey(e.target.value)}
            />
            <Button size="sm" variant="secondary" onClick={() => setShowGroqKey((v) => !v)}>
              {showGroqKey ? 'Hide' : 'Show'}
            </Button>
          </div>
          <p className="mt-1 text-[11px] text-slate-400">Get a key at console.groq.com — starts with gsk_. Leave blank to keep current key and only change model.</p>
        </Field>
        <Field label="Model">
          <select
            className="field"
            value={groqModel}
            onChange={(e) => setGroqModel(e.target.value)}
          >
            <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (recommended)</option>
            <option value="openai/gpt-oss-20b">openai/gpt-oss-20b</option>
            <option value="llama3-8b-8192">llama3-8b-8192 (fast)</option>
            <option value="llama3-70b-8192">llama3-70b-8192</option>
            <option value="mixtral-8x7b-32768">mixtral-8x7b-32768</option>
          </select>
          <p className="mt-1 text-[11px] text-slate-400">Or type a custom model name:</p>
          <input
            className="field mt-1"
            value={groqModel}
            onChange={(e) => setGroqModel(e.target.value)}
            placeholder="llama-3.3-70b-versatile"
          />
        </Field>
        <Button size="sm" onClick={saveGroq} disabled={groqSaving}>
          {groqSaving ? 'Saving…' : 'Save Groq settings'}
        </Button>
      </Card>

      <Card>
        <h2 className="text-sm font-semibold text-danger-600">Sign out</h2>
        <p className="mt-1 text-xs text-slate-500">
          Sign out of this session and return to the login page.
        </p>
        <Button className="mt-4" variant="dangerOutline" onClick={signOut}>
          Sign out
        </Button>
      </Card>
    </div>
  )
}

function Toggle({ label, description, checked, onChange }) {
  return (
    <button
      type="button"
      onClick={onChange}
      className="flex w-full items-center justify-between gap-4 rounded-lg border border-slate-100 px-3 py-3 text-left hover:bg-slate-50"
    >
      <div>
        <p className="text-sm font-medium text-slate-800">{label}</p>
        <p className="text-xs text-slate-400">{description}</p>
      </div>
      <span
        className={`relative h-6 w-11 shrink-0 rounded-full transition ${
          checked ? 'bg-navy-900' : 'bg-slate-200'
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${
            checked ? 'left-5' : 'left-0.5'
          }`}
        />
      </span>
    </button>
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
