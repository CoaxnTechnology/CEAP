import { useEffect, useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'
import { tasks as seedTasks } from '../data/osData'

export default function Tasks() {
  const { toast } = useApp()
  const [items, setItems] = useState(seedTasks)
  const [showNew, setShowNew] = useState(false)
  const [form, setForm] = useState({ title: '', assignee: '', workspace: 'general', priority: 'medium' })
  const [saving, setSaving] = useState(false)
  const [staff, setStaff] = useState([])

  useEffect(() => {
    api('/api/tasks')
      .then((r) => setItems(r.tasks))
      .catch(() => setItems(seedTasks))
    api('/api/staff')
      .then((users) => setStaff(users || []))
      .catch(() => setStaff([]))
  }, [])

  async function complete(id) {
    const target = items.find((t) => t.id === id)
    try {
      const r = await api(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'done' }) })
      setItems((list) => list.map((t) => (t.id === id ? r.task : t)))
      toast('Task completed', 'success')
    } catch {
      toast(`Could not complete: ${target?.title}`)
    }
  }

  async function createTask() {
    const title = form.title.trim()
    if (!title) {
      toast('Task title is required', 'error')
      return
    }
    setSaving(true)
    try {
      const r = await api('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
          title,
          assignee: form.assignee.trim(),
          workspace: form.workspace,
          priority: form.priority,
        }),
      })
      setItems((list) => [r.task, ...list])
      setShowNew(false)
      setForm({ title: '', assignee: '', workspace: 'general', priority: 'medium' })
      toast('Task created', 'success')
    } catch {
      toast('Could not create task', 'error')
    } finally {
      setSaving(false)
    }
  }

  const field = 'w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none focus:border-navy-400 focus:bg-white'

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Tasks"
        subtitle="Cross-workspace work queue for the school operating system."
        actions={
          <Button size="sm" onClick={() => setShowNew(true)}>
            New task
          </Button>
        }
      />

      <Section title={`${items.filter((t) => t.status !== 'done').length} open`} padding={false}>
        <ul className="divide-y divide-slate-50">
          {items.map((t) => (
            <li key={t.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className={`text-sm font-medium ${t.status === 'done' ? 'text-slate-400 line-through' : 'text-slate-800'}`}>
                  {t.title}
                </p>
                <p className="text-[11px] text-slate-400">
                  {t.assignee || t.owner} · Due {t.due} · {t.workspace}
                </p>
              </div>
              <StatusBadge
                status={
                  t.status === 'done'
                    ? 'Current'
                    : t.priority === 'urgent'
                      ? 'Missing'
                      : t.priority === 'high'
                        ? 'Expiring'
                        : 'Draft'
                }
              />
              {t.status !== 'done' && (
                <Button size="sm" variant="secondary" onClick={() => complete(t.id)}>
                  Complete
                </Button>
              )}
            </li>
          ))}
        </ul>
      </Section>

      <Modal open={showNew} onClose={() => setShowNew(false)} title="New task">
        <div className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Title</label>
            <input
              className={field}
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Approve leave request"
              autoFocus
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-600">Assignee</label>
            <select
              className={field}
              value={form.assignee}
              onChange={(e) => setForm({ ...form, assignee: e.target.value })}
            >
              <option value="">Select a user</option>
              {staff
                .filter((u) => u.status !== 'disabled')
                .map((u) => (
                  <option key={u.email} value={u.full_name || u.email}>{u.full_name || u.email}</option>
                ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Workspace</label>
              <select className={field} value={form.workspace} onChange={(e) => setForm({ ...form, workspace: e.target.value })}>
                {['general', 'hr', 'finance', 'academic', 'admissions', 'compliance', 'studio'].map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Priority</label>
              <select className={field} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {['low', 'medium', 'high', 'urgent'].map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button size="sm" variant="secondary" onClick={() => setShowNew(false)}>Cancel</Button>
            <Button size="sm" onClick={createTask} disabled={saving}>
              {saving ? 'Creating…' : 'Create task'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}