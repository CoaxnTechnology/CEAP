import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Shield, Plus } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

const PANELS = [
  'Executive', 'Academic', 'Students', 'Admissions', 'Finance', 'HR',
  'Compliance', 'Knowledge', 'AI Studio', 'Admin',
  'Tasks', 'Approvals', 'Calendar', 'Analytics', 'Workflows',
]

const toArray = (p) => (Array.isArray(p) ? p : p ? [p] : [])
const toggle = (arr, item) => arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item]

export default function RolesAdmin() {
  const navigate = useNavigate()
  const { toast } = useApp()
  const [roles, setRoles] = useState([])
  const [edit, setEdit] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [newRole, setNewRole] = useState({ name: '', permissions: [], users: 0 })

  useEffect(() => {
    api('/api/roles').then((rs) => setRoles(rs.map((r) => ({ ...r, permissions: toArray(r.permissions) })))).catch((e) => toast(e.message, 'warning'))
  }, [])

  async function saveEdit() {
    try {
      const saved = await api(`/api/roles/${edit.id}`, { method: 'PUT', body: JSON.stringify(edit) })
      setRoles((prev) => prev.map((r) => (r.id === saved.id ? saved : r)))
      toast(`Role "${saved.name}" updated`, 'success')
      setEdit(null)
    } catch (e) { toast(e.message, 'warning') }
  }

  async function addRole() {
    if (!newRole.name.trim()) { toast('Role name required', 'warning'); return }
    try {
      const saved = await api('/api/roles', { method: 'POST', body: JSON.stringify(newRole) })
      setRoles((prev) => [...prev, saved])
      toast(`Role "${saved.name}" created`, 'success')
      setAddOpen(false)
      setNewRole({ name: '', permissions: [], users: 0 })
    } catch (e) { toast(e.message, 'warning') }
  }

  async function deleteRole() {
    if (!window.confirm(`Delete role "${edit.name}"?`)) return
    try {
      await api(`/api/roles/${edit.id}`, { method: 'DELETE' })
      setRoles((prev) => prev.filter((r) => r.id !== edit.id))
      toast(`Role "${edit.name}" deleted`, 'success')
      setEdit(null)
    } catch (e) { toast(e.message, 'warning') }
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <button type="button" onClick={() => navigate('/admin')}
            className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:underline"
          ><ArrowLeft className="h-3.5 w-3.5" /> Back to Admin</button>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Roles & Permissions</h1>
          <p className="mt-1 text-sm text-slate-500">Control who can search, chat, generate, approve, and administer CEAP</p>
        </div>
        <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> Add role</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((r) => (
          <Card key={r.id}>
            <div className="flex items-start justify-between">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-50 text-navy-700"><Shield className="h-5 w-5" /></div>
              <Button size="sm" variant="secondary" onClick={() => setEdit({ ...r })}>Edit</Button>
            </div>
            <h3 className="mt-3 text-base font-semibold text-slate-900">{r.name}</h3>
            <p className="mt-1 text-2xl font-bold text-navy-800">{r.users}</p>
            <p className="text-[11px] text-slate-400">assigned users</p>
            <p className="mt-2 flex flex-wrap gap-1">
              {toArray(r.permissions).length
                ? toArray(r.permissions).map((p) => (
                    <span key={p} className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600">{p}</span>
                  ))
                : <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-400">No panels</span>}
            </p>
          </Card>
        ))}
      </div>

      <Card className="border-navy-100 bg-navy-50">
        <p className="text-sm font-semibold text-navy-900">Permission model</p>
        <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-navy-800/80">
          {[
            ['Principal', 'All workspaces — Executive, Academic, Students, Admissions, Finance, HR, Compliance, Knowledge, AI Studio, Admin, plus operations'],
            ['HOD', 'Academic, Students, Knowledge, AI Studio — generate and review within dept'],
            ['Teacher', 'Academic, Students, AI Studio — search + AI chat with citations'],
            ['Admin Staff', 'Compliance, Knowledge, Finance — evidence + source connectors'],
            ['Viewer', 'Executive, Knowledge — read-only search'],
          ].map(([role, scope]) => <li key={role}><strong>{role}</strong> — {scope}</li>)}
        </ul>
      </Card>

      <Modal open={!!edit} onClose={() => setEdit(null)} title="Edit role"
        footer={<><Button variant="dangerOutline" onClick={deleteRole}>Delete</Button><div className="flex-1" /><Button variant="secondary" onClick={() => setEdit(null)}>Cancel</Button><Button onClick={saveEdit}>Save</Button></>}
      >
        {edit && (
          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Name</label>
              <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-400"
                value={edit.name} onChange={(e) => setEdit((r) => ({ ...r, name: e.target.value }))} />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-500">Permitted panels</label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {PANELS.map((p) => (
                  <label key={p} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-navy-400">
                    <input type="checkbox" className="h-4 w-4 accent-navy-700"
                      checked={edit.permissions.includes(p)}
                      onChange={() => setEdit((r) => ({ ...r, permissions: toggle(r.permissions, p) }))} />
                    {p}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add role"
        footer={<><Button variant="secondary" onClick={() => setAddOpen(false)}>Cancel</Button><Button onClick={addRole}>Create role</Button></>}
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Name</label>
            <input className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-400"
              value={newRole.name} onChange={(e) => setNewRole((r) => ({ ...r, name: e.target.value }))} placeholder="e.g. Compliance Officer" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Permitted panels</label>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {PANELS.map((p) => (
                <label key={p} className="flex cursor-pointer items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-700 hover:border-navy-400">
                  <input type="checkbox" className="h-4 w-4 accent-navy-700"
                    checked={newRole.permissions.includes(p)}
                    onChange={() => setNewRole((r) => ({ ...r, permissions: toggle(r.permissions, p) }))} />
                  {p}
                </label>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
