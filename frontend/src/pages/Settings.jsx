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

  useEffect(() => {
    api('/api/settings/targets')
      .then(setTargets)
      .catch(() => {})
  }, [])

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
