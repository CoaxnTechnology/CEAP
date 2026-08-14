import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { UserPlus, Search, ArrowLeft, MoreHorizontal, Mail } from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const DEPARTMENTS = ['Academic', 'HR', 'Finance', 'Admin', 'Compliance', 'Transport', 'IT', 'Sports']
const ROLES = ['Principal', 'HOD', 'Teacher', 'Admin Staff', 'Viewer']

export default function UsersAdmin() {
  const navigate = useNavigate()
  const { toast } = useApp()
  const [users, setUsers] = useState([])
  const [query, setQuery] = useState('')
  const [inviteOpen, setInviteOpen] = useState(false)
  const [editUser, setEditUser] = useState(null)
  const [tempPw, setTempPw] = useState(null)
  const [form, setForm] = useState({ name: '', email: '', role: 'Teacher', department: 'Academic' })

  const fetchUsers = () => {
    api('/api/staff')
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        setUsers(list.map((u) => ({
          id: u.email,
          name: u.full_name || u.email.split('@')[0],
          email: u.email,
          role: u.role || 'user',
          department: u.department || '',
          status: u.status === 'active' ? 'Active' : u.status === 'invited' ? 'Invited' : u.status || 'Active',
          lastActive: u.created_at ? new Date(u.created_at * 1000).toLocaleDateString() : '—',
        })))
      })
      .catch(() => setUsers([]))
  }

  useEffect(fetchUsers, [])

  const filtered = users.filter(
    (u) =>
      !query ||
      u.name.toLowerCase().includes(query.toLowerCase()) ||
      u.email.toLowerCase().includes(query.toLowerCase()) ||
      u.role.toLowerCase().includes(query.toLowerCase())
  )

  async function invite() {
    if (!form.email.trim() || !form.name.trim()) {
      toast('Name and email required', 'warning')
      return
    }
    try {
      const res = await api('/api/staff', {
        method: 'POST',
        body: JSON.stringify({
          email: form.email,
          full_name: form.name,
          role: form.role,
          department: form.department,
          invite: true,
        }),
      })
      setInviteOpen(false)
      setTempPw({ email: form.email, password: res.temp_password || '', emailSent: !!res.email_sent })
      setForm({ name: '', email: '', role: 'Teacher', department: 'Academic' })
      fetchUsers()
    } catch (e) { toast(e.message || 'Invite failed', 'error') }
  }

  async function saveUser() {
    if (!editUser) return
    try {
      await api(`/api/staff/${encodeURIComponent(editUser.email)}`, {
        method: 'PUT',
        body: JSON.stringify({
          full_name: editUser.name,
          role: editUser.role,
          department: editUser.department,
          status: editUser.status === 'Active' ? 'active' : editUser.status === 'Invited' ? 'invited' : 'disabled',
        }),
      })
      toast(`Updated ${editUser.name}`, 'success')
      setEditUser(null)
      fetchUsers()
    } catch (e) { toast(e.message || 'Save failed', 'error') }
  }

  async function removeUser(u) {
    if (!confirm(`Remove ${u.name}?`)) return
    try {
      await api(`/api/staff/${encodeURIComponent(u.email)}`, { method: 'DELETE' })
      toast(`Removed ${u.name}`, 'info')
      setEditUser(null)
      fetchUsers()
    } catch (e) { toast(e.message || 'Remove failed', 'error') }
  }

  function resendInvite(u) {
    toast(`Invite re-sent to ${u.email}`, 'success')
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <button type="button" onClick={() => navigate('/admin')}
            className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-navy-600 hover:underline"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to Admin
          </button>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Users</h1>
          <p className="mt-1 text-sm text-slate-500">Invite staff and manage access</p>
        </div>
        <Button onClick={() => setInviteOpen(true)}><UserPlus className="h-4 w-4" /> Invite User</Button>
      </div>

      <div className="relative max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search users…"
          className="w-full rounded-lg border border-slate-200 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100" />
      </div>

      <Card padding={false}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-5 py-3">User</th>
                <th className="px-3 py-3">Role</th>
                <th className="px-3 py-3">Department</th>
                <th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Last active</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {filtered.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/80">
                  <td className="px-5 py-3.5">
                    <p className="font-medium text-slate-800">{u.name}</p>
                    <p className="text-xs text-slate-400">{u.email}</p>
                  </td>
                  <td className="px-3 py-3.5 text-slate-600">{u.role}</td>
                  <td className="px-3 py-3.5 text-slate-500">{u.department}</td>
                  <td className="px-3 py-3.5"><StatusBadge status={u.status} /></td>
                  <td className="px-3 py-3.5 text-xs text-slate-500">{u.lastActive}</td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center justify-end gap-1">
                      {u.status === 'Invited' && (
                        <button type="button" onClick={() => resendInvite(u)}
                          className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-navy-700" title="Resend invite"
                        ><Mail className="h-4 w-4" /></button>
                      )}
                      <button type="button" onClick={() => setEditUser({ ...u })}
                        className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
                      ><MoreHorizontal className="h-4 w-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Modal open={inviteOpen} onClose={() => setInviteOpen(false)} title="Invite user"
        footer={<>
          <Button variant="secondary" onClick={() => setInviteOpen(false)}>Cancel</Button>
          <Button onClick={invite}><UserPlus className="h-4 w-4" /> Send invite</Button>
        </>}
      >
        <div className="space-y-3">
          <Field label="Full name">
            <input className="field" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
          </Field>
          <Field label="Email">
            <input type="email" className="field" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
          </Field>
          <Field label="Role">
            <select className="field" value={form.role} onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </Field>
          <Field label="Department">
            <select className="field" value={form.department} onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}>
              {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </Field>
        </div>
      </Modal>

      <Modal open={!!tempPw} onClose={() => setTempPw(null)} title="Invitation created"
        footer={<>
          <Button variant="secondary" onClick={() => setTempPw(null)}>Close</Button>
        </>}
      >
        {tempPw && (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">
              {tempPw.email} can sign in with this temporary password. They will be asked to set their own on first login.
            </p>
            <p className={`text-xs font-medium ${tempPw.emailSent ? 'text-emerald-600' : 'text-amber-600'}`}>
              {tempPw.emailSent
                ? `Invitation email sent to ${tempPw.email}.`
                : 'Invitation email could not be sent — no email config. Share the password manually.'}
            </p>
            <div className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <code className="font-mono text-sm text-navy-800">{tempPw.password}</code>
              <button type="button" onClick={() => { navigator.clipboard?.writeText(tempPw.password); toast('Password copied', 'success') }}
                className="rounded-md px-2 py-1 text-xs font-medium text-navy-700 hover:bg-slate-200">
                Copy
              </button>
            </div>
          </div>
        )}
      </Modal>

      <Modal open={!!editUser} onClose={() => setEditUser(null)} title="Edit user"
        footer={editUser && <>
          <Button variant="dangerOutline" onClick={() => removeUser(editUser)}>Remove</Button>
          <Button variant="secondary" onClick={() => setEditUser(null)}>Cancel</Button>
          <Button onClick={saveUser}>Save changes</Button>
        </>}
      >
        {editUser && (
          <div className="space-y-3">
            <Field label="Name">
              <input className="field" value={editUser.name} onChange={(e) => setEditUser((u) => ({ ...u, name: e.target.value }))} />
            </Field>
            <Field label="Role">
              <select className="field" value={editUser.role} onChange={(e) => setEditUser((u) => ({ ...u, role: e.target.value }))}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </Field>
            <Field label="Department">
              <select className="field" value={editUser.department} onChange={(e) => setEditUser((u) => ({ ...u, department: e.target.value }))}>
                {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </Field>
            <Field label="Status">
              <select className="field" value={editUser.status} onChange={(e) => setEditUser((u) => ({ ...u, status: e.target.value }))}>
                <option>Active</option>
                <option>Invited</option>
                <option>Suspended</option>
              </select>
            </Field>
          </div>
        )}
      </Modal>
    </div>
  )
}

function Field({ label, children }) {
  return <div><label className="mb-1 block text-xs font-medium text-slate-500">{label}</label>{children}</div>
}
