import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Section from '../components/ui/Section'
import Button from '../components/ui/Button'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

export default function CalendarPage() {
  const { toast } = useApp()
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [scheduling, setScheduling] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ title: '', date: '', time: '', type: 'Meeting' })

  useEffect(() => {
    api('/api/calendar')
      .then((d) => setEvents(d.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false))
  }, [])

  const all = [...events]
    .map((e) => ({
      id: `c-${e.id}`,
      title: e.title,
      date: e.date,
      time: e.time,
      type: e.type,
      status: e.status,
    }))
    .sort((a, b) => a.date.localeCompare(b.date))

  const refresh = async () => {
    const d = await api('/api/calendar')
    setEvents(d.events || [])
  }

  const handleSchedule = async (e) => {
    e.preventDefault()
    if (!form.title.trim()) return
    try {
      await api('/api/calendar', { method: 'POST', body: JSON.stringify(form) })
      setForm({ title: '', date: '', time: '', type: 'Meeting' })
      setScheduling(false)
      await refresh()
      toast('Event scheduled', 'success')
    } catch {
      toast('Failed to schedule', 'error')
    }
  }

  const openEdit = (e) => {
    setEditing(e)
    setForm({ title: e.title, date: e.date, time: e.time, type: e.type })
  }

  const handleEdit = async (e) => {
    e.preventDefault()
    if (!form.title.trim() || !editing) return
    try {
      await api(`/api/calendar/${editing.id.replace(/^c-/, '')}`, {
        method: 'PUT',
        body: JSON.stringify(form),
      })
      setEditing(null)
      setForm({ title: '', date: '', time: '', type: 'Meeting' })
      await refresh()
      toast('Event updated', 'success')
    } catch {
      toast('Failed to update', 'error')
    }
  }

  const handleDelete = async (e) => {
    if (!confirm(`Delete "${e.title}"?`)) return
    try {
      await api(`/api/calendar/${e.id.replace(/^c-/, '')}`, { method: 'DELETE' })
      await refresh()
      toast('Event deleted', 'info')
    } catch {
      toast('Failed to delete', 'error')
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Calendar"
        subtitle="School-wide events, inspections, and meetings in one stream."
        actions={
          <Button size="sm" onClick={() => setScheduling(true)}>
            Schedule
          </Button>
        }
      />

      {scheduling && (
        <form onSubmit={handleSchedule} className="flex flex-wrap gap-2 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <input required placeholder="Title" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input type="date" required className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          <input type="time" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} />
          <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option>Meeting</option><option>Admissions</option><option>Compliance</option><option>Academic</option><option>Finance</option><option>HR</option><option>Parent</option><option>Training</option>
          </select>
          <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.status || 'Upcoming'} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option>Upcoming</option><option>In Progress</option><option>Completed</option>
          </select>
          <div className="flex gap-2">
            <Button size="sm" type="submit">Save</Button>
            <Button size="sm" variant="ghost" type="button" onClick={() => setScheduling(false)}>Cancel</Button>
          </div>
        </form>
      )}

      {editing && (
        <form onSubmit={handleEdit} className="flex flex-wrap gap-2 rounded-xl border border-navy-200 bg-navy-50 p-4 shadow-sm">
          <input required placeholder="Title" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <input type="date" required className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
          <input type="time" className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.time} onChange={(e) => setForm({ ...form, time: e.target.value })} />
          <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
            <option>Meeting</option><option>Admissions</option><option>Compliance</option><option>Academic</option><option>Finance</option><option>HR</option><option>Parent</option><option>Training</option>
          </select>
          <select className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm outline-none focus:border-navy-400" value={form.status || 'Upcoming'} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            <option>Upcoming</option><option>In Progress</option><option>Completed</option>
          </select>
          <div className="flex gap-2">
            <Button size="sm" type="submit">Save</Button>
            <Button size="sm" variant="ghost" type="button" onClick={() => setEditing(null)}>Cancel</Button>
          </div>
        </form>
      )}

      <Section title="Upcoming" padding={false}>
        {loading ? (
          <div className="py-10 text-center text-slate-400">Loading calendar…</div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {all.map((e) => (
              <li key={e.id} className="flex gap-4 px-5 py-4">
                <div className="w-20 shrink-0">
                  <p className="text-sm font-bold text-navy-800">{e.date.slice(5)}</p>
                  <p className="text-[11px] text-slate-400">{e.time}</p>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-900">{e.title}</p>
                  <p className="text-[11px] text-slate-400">{e.type}</p>
                </div>
                <div className="flex shrink-0 gap-1">
                  <Button size="sm" variant="ghost" onClick={() => openEdit(e)}>
                    Open
                  </Button>
                  {e.id.startsWith('c-') && (
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(e)} className="text-slate-400 hover:text-danger-500">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </div>
  )
}