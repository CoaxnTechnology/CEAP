import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  GraduationCap,
  School,
  Building2,
  Users,
  Cloud,
  CheckCircle2,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  AlertCircle,
  Loader2,
} from 'lucide-react'
import { useApp } from '../../context/AppContext'
import Button from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import { api } from '../../lib/api'

const STEPS = [
  { id: 1, label: 'School profile', icon: School },
  { id: 2, label: 'Departments', icon: Building2 },
  { id: 3, label: 'Admin & roles', icon: Users },
  { id: 4, label: 'Connect sources', icon: Cloud },
  { id: 5, label: 'Review & launch', icon: Sparkles },
]

export default function Onboarding() {
  const { user, completeOnboarding, toast } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [school, setSchool] = useState({
    name: '',
    board: 'CBSE',
    city: '',
    state: '',
    academicYear: '2025-26',
    studentCount: '',
    staffCount: '',
    address: '',
    phone: '',
    website: '',
  })

  const [depts, setDepts] = useState([])
  const [roles, setRoles] = useState([])
  const [adminName, setAdminName] = useState(user?.name || '')
  const [adminRole, setAdminRole] = useState('Principal')
  const [inviteEmails, setInviteEmails] = useState('')
  const [invitedUsers, setInvitedUsers] = useState([])

  const [odStatus, setOdStatus] = useState({
    id: 'onedrive',
    name: 'OneDrive',
    description: 'Microsoft 365 school tenant documents',
    status: 'Not Connected',
    lastSync: null,
    connected: false,
  })
  const [odConnecting, setOdConnecting] = useState(false)

  function saveOnboardingState() {
    try {
      sessionStorage.setItem('onboarding_step', String(step))
      sessionStorage.setItem('onboarding_school', JSON.stringify(school))
      sessionStorage.setItem('onboarding_depts', JSON.stringify(depts))
      sessionStorage.setItem('onboarding_admin_name', adminName)
      sessionStorage.setItem('onboarding_admin_role', adminRole)
      sessionStorage.setItem('onboarding_invite_emails', inviteEmails)
      sessionStorage.setItem('onboarding_od_connected', String(odStatus.connected))
    } catch {}
  }

  useEffect(() => {
    // Restore state from sessionStorage if returning from OAuth
    const savedStep = sessionStorage.getItem('onboarding_step')
    if (savedStep) {
      const s = parseInt(savedStep, 10)
      if (s >= 1 && s <= 5) setStep(s)
      try {
        const savedSchool = JSON.parse(sessionStorage.getItem('onboarding_school') || '{}')
        if (savedSchool.name) setSchool(savedSchool)
        const savedDepts = JSON.parse(sessionStorage.getItem('onboarding_depts') || '[]')
        if (savedDepts.length) setDepts(savedDepts)
      } catch {}
      const savedName = sessionStorage.getItem('onboarding_admin_name')
      if (savedName) setAdminName(savedName)
      const savedRole = sessionStorage.getItem('onboarding_admin_role')
      if (savedRole) setAdminRole(savedRole)
      const savedInvites = sessionStorage.getItem('onboarding_invite_emails')
      if (savedInvites) setInviteEmails(savedInvites)
      const savedOd = sessionStorage.getItem('onboarding_od_connected')
      if (savedOd === 'true') {
        setOdStatus((prev) => ({ ...prev, status: 'Connected', connected: true }))
      }
      // Check if returning from OneDrive OAuth
      const params = new URLSearchParams(window.location.search)
      if (params.get('od_connected') === '1') {
        setOdStatus((prev) => ({ ...prev, status: 'Connected', connected: true }))
        toast('OneDrive connected successfully', 'success')
      }
      // Clear saved state
      sessionStorage.removeItem('onboarding_step')
      sessionStorage.removeItem('onboarding_school')
      sessionStorage.removeItem('onboarding_depts')
      sessionStorage.removeItem('onboarding_admin_name')
      sessionStorage.removeItem('onboarding_admin_role')
      sessionStorage.removeItem('onboarding_invite_emails')
      sessionStorage.removeItem('onboarding_od_connected')
    }
  }, [])

  useEffect(() => {
    async function loadDefaults() {
      try {
        const [deptsRes, rolesRes] = await Promise.all([
          api('/api/onboarding/departments'),
          api('/api/onboarding/roles'),
        ])
        setDepts((deptsRes.departments || []).map((d) => ({ ...d, enabled: d.id !== 'it' && d.id !== 'sports' && d.id !== 'library' })))
        setRoles(rolesRes.roles || [])
      } catch (e) {
        setDepts([
          { id: 'academic', name: 'Academic', code: 'ACAD', enabled: true },
          { id: 'hr', name: 'HR', code: 'HR', enabled: true },
          { id: 'finance', name: 'Finance', code: 'FIN', enabled: true },
          { id: 'admin', name: 'Admin', code: 'ADMIN', enabled: true },
          { id: 'transport', name: 'Transport', code: 'TRANS', enabled: true },
          { id: 'it', name: 'IT', code: 'IT', enabled: false },
          { id: 'sports', name: 'Sports', code: 'SPORT', enabled: false },
          { id: 'library', name: 'Library', code: 'LIB', enabled: false },
        ])
        setRoles([
          { name: 'Principal', description: 'Full access to all modules' },
          { name: 'HOD', description: 'Department head' },
          { name: 'Teacher', description: 'Academic access' },
          { name: 'Admin Staff', description: 'Admin operations' },
          { name: 'Viewer', description: 'Read-only access' },
        ])
      }
      setLoading(false)
    }
    loadDefaults()

    // Check OneDrive status
    api('/api/onboarding/connectors/onedrive').then((res) => {
      setOdStatus(res)
    }).catch(() => {})
  }, [])

  function updateSchool(field, value) {
    setSchool((s) => ({ ...s, [field]: value }))
  }

  function toggleDept(id) {
    setDepts((list) =>
      list.map((d) => (d.id === id ? { ...d, enabled: !d.enabled } : d))
    )
  }

  async function connectOneDrive() {
    setOdConnecting(true)
    saveOnboardingState()
    try {
      const res = await api('/api/onboarding/connectors/onedrive/connect', { method: 'POST' })
      if (res.auth_url) {
        window.location.href = res.auth_url
        return
      }
      setOdStatus((prev) => ({ ...prev, status: 'Connected', connected: true }))
      toast('OneDrive connected successfully', 'success')
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed to connect OneDrive', 'error')
    }
    setOdConnecting(false)
  }

  function disconnectOneDrive() {
    api('/api/onboarding/connectors/onedrive/disconnect', { method: 'POST' })
      .then(() => {
        setOdStatus({ ...odStatus, status: 'Not Connected', connected: false, lastSync: null })
        toast('OneDrive disconnected', 'info')
      })
      .catch(() => {})
  }

  function canNext() {
    if (step === 1) {
      return school.name.trim() && school.city.trim() && school.state.trim()
    }
    if (step === 2) {
      return depts.some((d) => d.enabled)
    }
    if (step === 3) {
      return adminName.trim() && adminRole
    }
    return true
  }

  async function handleFinish() {
    setSaving(true)
    setError('')
    try {
      const enabledDeptIds = depts.filter((d) => d.enabled).map((d) => d.id)
      const emailList = inviteEmails
        .split(',')
        .map((e) => e.trim())
        .filter(Boolean)

      await api('/api/onboarding/school', {
        method: 'POST',
        body: JSON.stringify({
          school: {
            ...school,
            studentCount: Number(school.studentCount) || 0,
            staffCount: Number(school.staffCount) || 0,
            code: school.name.split(' ').slice(0, 2).join('').toUpperCase(),
          },
          departments: enabledDeptIds,
          admin: {
            name: adminName,
            role: adminRole,
          },
          invitations: emailList.map((email) => ({ email, role: 'Teacher' })),
          connectors: odStatus.connected ? [{ id: 'onedrive', status: 'Connected' }] : [],
        }),
      })

      completeOnboarding({
        school: {
          ...school,
          studentCount: Number(school.studentCount) || 0,
          staffCount: Number(school.staffCount) || 0,
          departments: depts.filter((d) => d.enabled).map((d) => d.name),
        },
        connectors: odStatus.connected
          ? [{ id: 'onedrive', name: 'OneDrive', status: 'Connected', lastSync: null }]
          : [],
      })
      toast('Welcome to CEAP! School onboarding complete.', 'success')
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Onboarding failed')
      toast('Onboarding failed. Please try again.', 'error')
    }
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-navy-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy-900 text-white">
              <GraduationCap className="h-4 w-4" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900">School Onboarding</p>
              <p className="text-[11px] text-slate-400">CEAP Education Edition</p>
            </div>
          </div>
          <p className="text-xs text-slate-500">
            Step {step} of {STEPS.length}
          </p>
        </div>
      </header>

      <div className="mx-auto max-w-4xl px-4 py-8">
        <ol className="mb-8 flex flex-wrap gap-2">
          {STEPS.map((s) => {
            const Icon = s.icon
            const active = step === s.id
            const done = step > s.id
            return (
              <li key={s.id} className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => s.id < step && setStep(s.id)}
                  className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                    active
                      ? 'bg-navy-900 text-white'
                      : done
                        ? 'bg-success-50 text-success-700'
                        : 'bg-white text-slate-400 border border-slate-200'
                  }`}
                >
                  {done ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Icon className="h-3.5 w-3.5" />}
                  <span className="hidden sm:inline">{s.label}</span>
                  <span className="sm:hidden">{s.id}</span>
                </button>
              </li>
            )
          })}
        </ol>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg border border-danger-100 bg-danger-50 px-4 py-3 text-sm text-danger-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <Card>
          {step === 1 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">School profile</h2>
                <p className="text-sm text-slate-500">
                  Tell us about your institution — used for compliance and knowledge context.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="School name *" className="sm:col-span-2">
                  <input
                    className="field"
                    value={school.name}
                    onChange={(e) => updateSchool('name', e.target.value)}
                    placeholder="e.g. Greenwood International School"
                  />
                </Field>
                <Field label="Board / Affiliation">
                  <select
                    className="field"
                    value={school.board}
                    onChange={(e) => updateSchool('board', e.target.value)}
                  >
                    <option>CBSE</option>
                    <option>ICSE</option>
                    <option>State Board</option>
                    <option>IB</option>
                    <option>Cambridge</option>
                    <option>Other</option>
                  </select>
                </Field>
                <Field label="Academic year">
                  <select
                    className="field"
                    value={school.academicYear}
                    onChange={(e) => updateSchool('academicYear', e.target.value)}
                  >
                    <option>2025-26</option>
                    <option>2024-25</option>
                    <option>2026-27</option>
                  </select>
                </Field>
                <Field label="City *">
                  <input
                    className="field"
                    value={school.city}
                    onChange={(e) => updateSchool('city', e.target.value)}
                    placeholder="Bengaluru"
                  />
                </Field>
                <Field label="State *">
                  <input
                    className="field"
                    value={school.state}
                    onChange={(e) => updateSchool('state', e.target.value)}
                    placeholder="Karnataka"
                  />
                </Field>
                <Field label="Approx. students">
                  <input
                    type="number"
                    className="field"
                    value={school.studentCount}
                    onChange={(e) => updateSchool('studentCount', e.target.value)}
                    placeholder="1200"
                  />
                </Field>
                <Field label="Approx. staff">
                  <input
                    type="number"
                    className="field"
                    value={school.staffCount}
                    onChange={(e) => updateSchool('staffCount', e.target.value)}
                    placeholder="85"
                  />
                </Field>
                <Field label="Address" className="sm:col-span-2">
                  <input
                    className="field"
                    value={school.address}
                    onChange={(e) => updateSchool('address', e.target.value)}
                    placeholder="Campus address"
                  />
                </Field>
                <Field label="Phone">
                  <input
                    className="field"
                    value={school.phone}
                    onChange={(e) => updateSchool('phone', e.target.value)}
                    placeholder="+91 …"
                  />
                </Field>
                <Field label="Website">
                  <input
                    className="field"
                    value={school.website}
                    onChange={(e) => updateSchool('website', e.target.value)}
                    placeholder="www.school.edu"
                  />
                </Field>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Departments</h2>
                <p className="text-sm text-slate-500">
                  Enable departments for knowledge scoping, AI chat context, and ownership.
                </p>
              </div>
              {depts.length === 0 ? (
                <p className="text-sm text-slate-400">No departments available. Please contact your admin.</p>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {depts.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => toggleDept(d.id)}
                      className={`flex items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                        d.enabled
                          ? 'border-navy-300 bg-navy-50 ring-1 ring-navy-100'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <span className="text-sm font-medium text-slate-800">{d.name}</span>
                      <span
                        className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                          d.enabled ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-400'
                        }`}
                      >
                        {d.enabled ? '✓' : ''}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Admin & roles</h2>
                <p className="text-sm text-slate-500">
                  You will be the primary admin. Optionally invite colleagues now.
                </p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Your full name">
                  <input
                    className="field"
                    value={adminName}
                    onChange={(e) => setAdminName(e.target.value)}
                    placeholder="Principal name"
                  />
                </Field>
                <Field label="Your role">
                  <select
                    className="field"
                    value={adminRole}
                    onChange={(e) => setAdminRole(e.target.value)}
                  >
                    {roles.map((r) => (
                      <option key={r.name} value={r.name}>{r.name}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Invite team (emails, comma-separated)" className="sm:col-span-2">
                  <textarea
                    className="field min-h-[80px]"
                    value={inviteEmails}
                    onChange={(e) => setInviteEmails(e.target.value)}
                    placeholder="hod@school.edu, hr@school.edu"
                  />
                </Field>
              </div>
              {invitedUsers.length > 0 && (
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-500 mb-2">Invited ({invitedUsers.length})</p>
                  <div className="flex flex-wrap gap-2">
                    {invitedUsers.map((u) => (
                      <span key={u.email} className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                        {u.email} <span className="text-primary/50">({u.role})</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-3 text-xs text-slate-500">
                Default roles created: {roles.map((r) => r.name).join(', ')}. You can refine
                permissions later under Admin → Manage Roles.
              </div>
            </div>
          )}

          {step === 4 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Connect knowledge sources</h2>
                <p className="text-sm text-slate-500">
                  Connect OneDrive to import school documents. You can skip and connect later.
                </p>
              </div>
              <div className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{odStatus.name}</p>
                  <p className="text-xs text-slate-500">{odStatus.description}</p>
                  {odStatus.lastSync && (
                    <p className="mt-1 text-[11px] text-success-600">Synced {odStatus.lastSync}</p>
                  )}
                </div>
                {odStatus.connected ? (
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success-100 text-success-600 text-[10px] font-bold">✓</span>
                    <Button variant="secondary" size="sm" onClick={disconnectOneDrive}>Disconnect</Button>
                  </div>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={connectOneDrive}
                    disabled={odConnecting}
                  >
                    {odConnecting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : 'Connect OneDrive'}
                  </Button>
                )}
              </div>
              <button
                type="button"
                onClick={() => setStep(5)}
                className="text-sm font-medium text-navy-600 hover:underline"
              >
                Skip for now →
              </button>
            </div>
          )}

          {step === 5 && (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Review & launch</h2>
                <p className="text-sm text-slate-500">
                  Confirm setup. You can change everything later in Admin.
                </p>
              </div>
              <dl className="grid gap-3 sm:grid-cols-2">
                <ReviewItem label="School" value={school.name || '—'} />
                <ReviewItem label="Board" value={school.board} />
                <ReviewItem label="Location" value={`${school.city}, ${school.state}`} />
                <ReviewItem label="Academic year" value={school.academicYear} />
                <ReviewItem
                  label="Departments"
                  value={depts.filter((d) => d.enabled).map((d) => d.name).join(', ')}
                />
                <ReviewItem label="Primary admin" value={`${adminName} (${adminRole})`} />
                <ReviewItem
                  label="OneDrive"
                  value={odStatus.connected ? 'Connected' : 'Not connected'}
                />
                <ReviewItem
                  label="Invites pending"
                  value={
                    inviteEmails
                      .split(',')
                      .map((e) => e.trim())
                      .filter(Boolean).length || '0'
                  }
                />
              </dl>
              <div className="rounded-xl border border-success-100 bg-success-50 p-4 text-sm text-success-800">
                After launch you will land on the dashboard with full access to Search, AI Chat, Compliance, Documents, and Admin.
              </div>
            </div>
          )}

          <div className="mt-8 flex items-center justify-between border-t border-slate-100 pt-5">
            {step === 1 ? (
              <Button
                variant="secondary"
                onClick={() => {
                  localStorage.removeItem('ceap_session_v1')
                  sessionStorage.clear()
                  window.location.href = '/login'
                }}
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Login
              </Button>
            ) : (
              <Button
                variant="secondary"
                onClick={() => setStep((s) => Math.max(1, s - 1))}
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            )}
            {step < 5 ? (
              <Button
                disabled={!canNext()}
                onClick={() => {
                  if (!canNext()) {
                    toast('Please fill required fields', 'warning')
                    return
                  }
                  setStep((s) => s + 1)
                }}
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleFinish} disabled={saving || !canNext()}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {saving ? 'Launching…' : 'Launch CEAP'}
              </Button>
            )}
          </div>
        </Card>
      </div>

      <style>{`
        .field {
          width: 100%;
          border-radius: 0.5rem;
          border: 1px solid #e2e8f0;
          background: #f8fafc;
          padding: 0.55rem 0.75rem;
          font-size: 0.875rem;
          outline: none;
        }
        .field:focus {
          border-color: #627d98;
          background: #fff;
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

function ReviewItem({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2.5">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-sm font-medium text-slate-800">{value}</dd>
    </div>
  )
}