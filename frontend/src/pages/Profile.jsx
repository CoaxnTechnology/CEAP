import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

export default function Profile() {
  const { user, school, dispatch, toast } = useApp()
  const navigate = useNavigate()
  const [form, setForm] = useState({
    name: user?.name || '',
    email: user?.email || '',
    role: user?.role || '',
    phone: '',
  })
  const [showLeave, setShowLeave] = useState(false)
  const [myData, setMyData] = useState({ balance: {}, leaves: [] })
  const [leaveTypes, setLeaveTypes] = useState([])
  const [leave, setLeave] = useState({
    leave_type: '',
    start_date: '',
    end_date: '',
    half_day: false,
    reason: '',
  })

  function loadMyLeaves() {
    return api('/api/hr/leaves/mine').then(setMyData)
  }

  useEffect(() => {
    loadMyLeaves().catch(() => {})
    api('/api/hr/overview')
      .then((d) => {
        setLeaveTypes(d.leaveTypes || [])
        setLeave((l) => ({ ...l, leave_type: l.leave_type || (d.leaveTypes || [])[0] || '' }))
      })
      .catch(() => {})
  }, [])

  function save(e) {
    e.preventDefault()
    const avatar = form.name
      .split(' ')
      .map((w) => w[0])
      .join('')
      .slice(0, 2)
      .toUpperCase()
    dispatch({
      type: 'UPDATE_USER',
      payload: { name: form.name, email: form.email, role: form.role, avatar },
    })
    toast('Profile updated', 'success')
  }

  function submitLeave() {
    if (!leave.start_date) {
      toast('Pick a start date', 'warning')
      return
    }
    api('/api/hr/leave', {
      method: 'POST',
      body: JSON.stringify({
        leave_type: leave.leave_type,
        start_date: leave.start_date,
        end_date: leave.end_date || leave.start_date,
        half_day: leave.half_day,
        reason: leave.reason,
      }),
    })
      .then((res) => {
        toast(res.message, 'success')
        setShowLeave(false)
        setLeave({ leave_type: 'annual', start_date: '', end_date: '', half_day: false, reason: '' })
        return loadMyLeaves()
      })
      .catch(() => toast('Could not submit leave request', 'warning'))
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Profile settings</h1>
          <p className="mt-1 text-sm text-slate-500">{school?.name}</p>
        </div>
        <Button size="sm" onClick={() => setShowLeave(true)}>
          Apply for leave
        </Button>
      </div>

      <Modal
        open={showLeave}
        onClose={() => setShowLeave(false)}
        title="Apply for leave"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setShowLeave(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={submitLeave}>
              Submit request
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Leave type</label>
            <select
              className="field"
              value={leave.leave_type}
              onChange={(e) => setLeave((l) => ({ ...l, leave_type: e.target.value }))}
            >
              {(leaveTypes.length ? leaveTypes : ['annual', 'sick', 'personal', 'maternity', 'paternity']).map(
                (t) => (
                  <option key={t} value={t}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </option>
                ),
              )}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Start date</label>
              <input
                type="date"
                className="field"
                value={leave.start_date}
                onChange={(e) => setLeave((l) => ({ ...l, start_date: e.target.value }))}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">End date</label>
              <input
                type="date"
                className="field"
                value={leave.end_date}
                onChange={(e) => setLeave((l) => ({ ...l, end_date: e.target.value }))}
              />
            </div>
          </div>
          <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300"
              checked={leave.half_day}
              onChange={(e) => setLeave((l) => ({ ...l, half_day: e.target.checked }))}
            />
            Half day
          </label>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Reason</label>
            <textarea
              className="field"
              rows="2"
              value={leave.reason}
              onChange={(e) => setLeave((l) => ({ ...l, reason: e.target.value }))}
              placeholder="Optional"
            />
          </div>
        </div>
      </Modal>

      <Card>
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-navy-900 text-lg font-bold text-white">
            {user?.avatar}
          </div>
          <div>
            <p className="font-semibold text-slate-900">{user?.name}</p>
            <p className="text-sm text-slate-500">{user?.role}</p>
          </div>
        </div>

        <form onSubmit={save} className="space-y-4">
          <Field label="Full name">
            <input
              className="field"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </Field>
          <Field label="Email">
            <input
              type="email"
              className="field"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
          </Field>
          <Field label="Role (display)">
            <input
              className="field"
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
            />
          </Field>
          <Field label="Phone (optional)">
            <input
              className="field"
              value={form.phone}
              onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
              placeholder="+91 …"
            />
          </Field>
          <div className="flex gap-2 pt-2">
            <Button type="submit">Save profile</Button>
            <Button type="button" variant="secondary" onClick={() => navigate('/settings')}>
              Preferences
            </Button>
          </div>
        </form>
      </Card>

      <Section
        title="My leave requests"
        subtitle={`Balance: ${Object.entries(myData.balance)
          .map(([k, v]) => `${k} ${v}d`)
          .join(' · ') || '—'}`}
        padding={false}
      >
        {myData.leaves.length === 0 ? (
          <p className="px-5 py-6 text-center text-sm text-slate-400">No leave requests yet.</p>
        ) : (
          <ul className="divide-y divide-slate-50">
            {myData.leaves.map((l) => (
              <li key={l.id} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {l.type.charAt(0).toUpperCase() + l.type.slice(1)} leave
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {l.dates}
                    {l.halfDay ? ' · Half day' : ''}
                  </p>
                </div>
                <StatusBadge
                  status={
                    l.status === 'approved'
                      ? 'Current'
                      : l.status === 'rejected'
                        ? 'Missing'
                        : 'Expiring'
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </Section>

      <style>{`.field{width:100%;border-radius:.5rem;border:1px solid #e2e8f0;background:#f8fafc;padding:.55rem .75rem;font-size:.875rem;outline:none}.field:focus{border-color:#627d98;background:#fff;box-shadow:0 0 0 2px #d9e2ec}`}</style>
    </div>
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
