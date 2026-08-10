import { useState, useEffect } from 'react'
import { CalendarDays, Clock, Users, MapPin, Plus, X } from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

export default function Meetings() {
  const { toast } = useApp()
  const [meetings, setMeetings] = useState([])
  const [open, setOpen] = useState(false)
  const [view, setView] = useState(null)
  const [form, setForm] = useState({
    title: '',
    date: '',
    time: '10:00 AM',
    agenda: '',
    attendees: '',
  })

  useEffect(() => {
    api('/api/meetings')
      .then((r) => setMeetings(r.meetings || []))
      .catch(() => toast('Could not load meetings', 'warning'))
  }, [])

  async function schedule() {
    if (!form.title.trim() || !form.date) {
      toast('Title and date are required', 'warning')
      return
    }
    try {
      const r = await api('/api/meetings', {
        method: 'POST',
        body: JSON.stringify({
          title: form.title,
          date: form.date,
          time: form.time,
          agenda: form.agenda,
          attendees: form.attendees
            ? form.attendees.split(',').map((a) => a.trim()).filter(Boolean)
            : [],
        }),
      })
      setMeetings((list) => [r.meeting, ...list])
      toast('Meeting scheduled', 'success')
      setOpen(false)
      setForm({ title: '', date: '', time: '10:00 AM', agenda: '', attendees: '' })
    } catch {
      toast('Could not schedule meeting', 'error')
    }
  }

  async function updateStatus(m, status, message) {
    try {
      const r = await api(`/api/meetings/${m.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      })
      setMeetings((list) => list.map((x) => (x.id === m.id ? r.meeting : x)))
      setView(null)
      toast(message, status === 'completed' ? 'success' : 'info')
    } catch {
      toast('Could not update meeting', 'error')
    }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Meetings</h1>
          <p className="mt-1 text-sm text-slate-500">
            Knowledge reviews, compliance syncs and training sessions
          </p>
        </div>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" />
          Schedule meeting
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {meetings.map((m) => (
          <Card key={m.id} onClick={() => setView(m)}>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-base font-semibold text-slate-900">{m.title}</h3>
              <StatusBadge status={m.status} />
            </div>
            <p className="mt-2 text-sm text-slate-500">{m.agenda}</p>
            <div className="mt-4 flex flex-wrap gap-4 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="h-3.5 w-3.5 text-navy-500" />
                {m.date}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-navy-500" />
                {m.time}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-navy-500" />
                Conference Room A
              </span>
            </div>
            <div className="mt-4 flex items-center gap-2 border-t border-slate-100 pt-3">
              <Users className="h-3.5 w-3.5 text-slate-400" />
              <p className="text-xs text-slate-500">{m.attendees.join(' · ')}</p>
            </div>
          </Card>
        ))}
      </div>

      {meetings.length === 0 && (
        <Card className="py-12 text-center">
          <CalendarDays className="mx-auto h-10 w-10 text-slate-300" />
          <p className="mt-3 text-sm text-slate-500">No meetings scheduled</p>
          <Button className="mt-4" onClick={() => setOpen(true)}>
            Schedule your first meeting
          </Button>
        </Card>
      )}

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Schedule meeting"
        footer={
          <>
            <Button variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button onClick={schedule}>
              <CalendarDays className="h-4 w-4" /> Schedule
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <Field label="Title *">
            <input
              className="field"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
              placeholder="Leadership Knowledge Review"
            />
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Date *">
              <input
                type="date"
                className="field"
                value={form.date}
                onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))}
              />
            </Field>
            <Field label="Time">
              <input
                className="field"
                value={form.time}
                onChange={(e) => setForm((f) => ({ ...f, time: e.target.value }))}
                placeholder="10:00 AM"
              />
            </Field>
          </div>
          <Field label="Agenda">
            <textarea
              className="field min-h-[70px]"
              value={form.agenda}
              onChange={(e) => setForm((f) => ({ ...f, agenda: e.target.value }))}
            />
          </Field>
          <Field label="Attendees (comma-separated)">
            <input
              className="field"
              value={form.attendees}
              onChange={(e) => setForm((f) => ({ ...f, attendees: e.target.value }))}
              placeholder="Priya Sharma, Rahul Mehta"
            />
          </Field>
        </div>
        <style>{`.field{width:100%;border-radius:.5rem;border:1px solid #e2e8f0;padding:.5rem .75rem;font-size:.875rem;outline:none}.field:focus{border-color:#627d98;box-shadow:0 0 0 2px #d9e2ec}`}</style>
      </Modal>

      <Modal
        open={!!view}
        onClose={() => setView(null)}
        title={view?.title || 'Meeting'}
        footer={
          view && (
            <>
              <Button variant="secondary" onClick={() => setView(null)}>
                Close
              </Button>
              {view.status !== 'Completed' && (
                <Button variant="success" onClick={() => updateStatus(view, 'completed', 'Meeting marked complete')}>
                  Mark completed
                </Button>
              )}
              <Button variant="dangerOutline" onClick={() => updateStatus(view, 'cancelled', 'Meeting cancelled')}>
                <X className="h-4 w-4" /> Cancel meeting
              </Button>
            </>
          )
        }
      >
        {view && (
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Status</dt>
              <dd>
                <StatusBadge status={view.status} />
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Date</dt>
              <dd className="font-medium">{view.date}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Time</dt>
              <dd className="font-medium">{view.time}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Agenda</dt>
              <dd className="mt-1 font-medium text-slate-800">{view.agenda}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Attendees</dt>
              <dd className="mt-1 text-slate-700">{view.attendees.join(', ')}</dd>
            </div>
          </dl>
        )}
      </Modal>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>
      {children}
    </div>
  )
}
