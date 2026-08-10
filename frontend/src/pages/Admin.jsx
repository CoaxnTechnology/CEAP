import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Cloud, FolderSync, UserPlus, Shield,
  CheckCircle2, Link2Off, RefreshCw, HardDrive,
  Upload, Settings, FileText, Trash2, Search,
} from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import FileUpload from '../components/ui/FileUpload'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const INITIAL_CONNECTORS = [
  { id: 'gdrive', name: 'Google Drive', description: 'Sync shared drives and policy folders', color: '#16a34a' },
  { id: 'onedrive', name: 'OneDrive', description: 'Microsoft school tenant documents', color: '#2563eb' },
  { id: 'dropbox', name: 'Dropbox', description: 'Shared team folders and archives', color: '#7c3aed' },
]

const connectorIcons = { gdrive: HardDrive, onedrive: Cloud, dropbox: FolderSync }

const SEED_ROLES = [
  { id: 1, name: 'Principal', users: 1, permissions: 'Full access' },
  { id: 2, name: 'HOD', users: 4, permissions: 'Dept knowledge + generate' },
  { id: 3, name: 'Teacher', users: 28, permissions: 'Search + AI Chat' },
  { id: 4, name: 'Admin Staff', users: 6, permissions: 'Compliance + connectors' },
  { id: 5, name: 'Viewer', users: 12, permissions: 'Read-only search' },
]

function nowLabel() {
  return new Date().toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

const API_BASE = import.meta.env.VITE_API_URL || ''

const DEPT_ORDER = ['HR', 'Admin', 'Finance', 'Academic', 'Compliance', 'Transport', 'IT', 'Sports']
const deptColors = { HR: '#ffe4e6', Admin: '#dbeafe', Finance: '#d1fae5', Academic: '#ede9fe', Compliance: '#fef3c7', Transport: '#cffafe', IT: '#e0e7ff', Sports: '#ffedd5' }
const deptTextColors = { HR: '#be123c', Admin: '#1d4ed8', Finance: '#047857', Academic: '#6d28d9', Compliance: '#b45309', Transport: '#0e7490', IT: '#4338ca', Sports: '#c2410c' }

function fmtDate(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
}

function deptBadge(dept) {
  const d = dept || 'Unclassified'
  return { bg: deptColors[d] || '#f1f5f9', text: deptTextColors[d] || '#475569', label: d }
}

export default function Admin() {
  const navigate = useNavigate()
  const { toast, school } = useApp()
  const [connStatus, setConnStatus] = useState({})  // { [id]: { connected: bool, lastSync: str } }
  const [manageConn, setManageConn] = useState(null)
  const [uploadOpen, setUploadOpen] = useState(false)
  const [files, setFiles] = useState([])
  const [filesLoading, setFilesLoading] = useState(true)
  const [odStatus, setOdStatus] = useState(null)
  const [odSyncing, setOdSyncing] = useState(false)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [fileSearch, setFileSearch] = useState('')

  const filteredFiles = useMemo(() => {
    const q = fileSearch.trim().toLowerCase()
    if (!q) return files
    return files.filter((f) => (f.name || '').toLowerCase().includes(q) || (f.department || '').toLowerCase().includes(q))
  }, [files, fileSearch])

  const connectorList = useMemo(() => INITIAL_CONNECTORS.map((c) => ({
    ...c,
    status: connStatus[c.id]?.connected ? 'Connected' : 'Not Connected',
    lastSync: connStatus[c.id]?.lastSync || null,
  })), [connStatus])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const justConnected = params.get('od_connected') === '1'
    if (justConnected) {
      window.history.replaceState({}, '', window.location.pathname)
    }
    api('/api/onedrive/status')
      .then((s) => {
        setOdStatus(s)
        if (s.connected) {
          setConnStatus((p) => ({ ...p, onedrive: { connected: true, lastSync: 'Just now' } }))
          if (justConnected) toast('OneDrive connected', 'success')
        }
      })
      .catch(() => {})
  }, [])

  const loadFiles = useCallback(() => {
    api('/api/files')
      .then((data) => {
        setFiles(Object.entries(data.files || {}).map(([id, f]) => ({ id, ...f })))
      })
      .catch(() => {})
      .finally(() => setFilesLoading(false))
  }, [])

  useEffect(() => { loadFiles() }, [])

  const handleManageClose = useCallback(() => setManageConn(null), [])
  const handleUploadClose = useCallback(() => { setUploadOpen(false); loadFiles() }, [loadFiles])

  function toggleSelect(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  function toggleSelectAll() {
    if (selectedIds.size === filteredFiles.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredFiles.map((f) => f.id)))
    }
  }

  async function deleteSelected() {
    if (!selectedIds.size) return
    if (!confirm(`Delete ${selectedIds.size} file${selectedIds.size !== 1 ? 's' : ''}?`)) return
    for (const id of selectedIds) {
      try {
        await api('/api/remove', {
          method: 'POST',
          body: JSON.stringify({ file_id: id }),
        })
      } catch {}
    }
    toast(`Deleted ${selectedIds.size} file${selectedIds.size !== 1 ? 's' : ''}`, 'info')
    setSelectedIds(new Set())
    loadFiles()
  }

  async function handleDelete(fileId) {
    if (!confirm('Delete this file?')) return
    try {
      const data = await api('/api/remove', {
        method: 'POST',
        body: JSON.stringify({ file_id: fileId }),
      })
      if (data.success) { toast('File deleted', 'info'); loadFiles() }
      else toast(data.error || 'Delete failed', 'error')
    } catch (err) { toast(err.message, 'error') }
  }

  function connect(c) {
    if (c.id === 'onedrive') {
      const s = odStatus || { enabled: false }
      if (s.enabled) { window.location.href = `${API_BASE}/onedrive/connect?redirect=${encodeURIComponent(window.location.origin + '/admin')}`; return }
      toast('OneDrive not configured by admin', 'warning')
      return
    }
    setConnStatus((p) => ({ ...p, [c.id]: { connected: true, lastSync: nowLabel() } }))
    toast(`${c.name} connected`, 'success')
    setManageConn(null)
  }

  function disconnect(c) {
    if (c.id === 'onedrive') {
      api('/api/onedrive/disconnect', { method: 'POST' }).catch(() => {})
    }
    setConnStatus((p) => ({ ...p, [c.id]: { connected: false, lastSync: null } }))
    toast(`${c.name} disconnected`, 'info')
    setManageConn(null)
  }

  async function syncOne(c) {
    if (c.id === 'onedrive') {
      setOdSyncing(true)
      try {
        const s = odStatus || { connected: false }
        if (!s.connected) { toast('Connect OneDrive first', 'warning'); return }

        async function listAll(token, folderId) {
          const data = await api(`/api/onedrive/files?folder=${folderId || 'root'}`)
          const rfiles = data.files || []
          const docs = []
          for (const f of rfiles) {
            if (f.isFolder) docs.push(...(await listAll(token, f.id)))
            else docs.push(f)
          }
          return docs
        }

        const docs = await listAll(s.token, 'root')
        if (!docs.length) { toast('No new files to import', 'info'); return }
        const importData = await api('/api/onedrive/import', {
          method: 'POST',
          body: JSON.stringify({ files: docs }),
        })
        setConnStatus((p) => ({ ...p, onedrive: { ...p.onedrive, lastSync: nowLabel() } }))
        toast(`Imported ${importData.imported?.length || 0} files from OneDrive`, 'success')
        loadFiles()
      } catch (err) { toast('OneDrive sync failed: ' + err.message, 'error') }
      finally { setOdSyncing(false) }
      return
    }
    if (!connStatus[c.id]?.connected) { toast('Connect first', 'warning'); return }
    setConnStatus((p) => ({ ...p, [c.id]: { ...p[c.id], lastSync: nowLabel() } }))
    toast(`${c.name} synced`, 'success')
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Admin</h1>
          <p className="mt-1 text-sm text-slate-500">
            {school?.name || 'Your school'} · Source connectors, folders, users and roles
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => navigate('/admin/roles')}>
            <Shield className="h-4 w-4" /> Manage Roles
          </Button>
          <Button onClick={() => navigate('/admin/users')}>
            <UserPlus className="h-4 w-4" /> Invite User
          </Button>
        </div>
      </div>

      {/* Connectors */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Source Connectors</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {connectorList.map((c) => {
            const Icon = connectorIcons[c.id] || Cloud
            const connected = c.status === 'Connected'
            return (
              <Card key={c.id} className="relative overflow-hidden">
                <div className="absolute left-0 top-0 h-1 w-full" style={{ backgroundColor: c.color }} />
                <div className="flex items-start justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl" style={{ backgroundColor: `${c.color}15`, color: c.color }}>
                    <Icon className="h-5 w-5" />
                  </div>
                  <StatusBadge status={c.status} />
                </div>
                <h3 className="mt-4 text-base font-semibold text-slate-900">{c.name}</h3>
                <p className="mt-1 text-sm text-slate-500">{c.description}</p>
                {connected ? (
                  <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
                    <CheckCircle2 className="h-3.5 w-3.5 text-success-500" />
                    Last synced {c.lastSync}
                  </p>
                ) : (
                  <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
                    <Link2Off className="h-3.5 w-3.5" />
                    Not connected
                  </p>
                )}
                <div className="mt-4 flex gap-2">
                  <Button className="flex-1" variant={connected ? 'secondary' : 'primary'} size="sm" onClick={() => { if (connected) setManageConn(c); else connect(c) }}>
                    {connected ? 'Manage' : 'Connect'}
                  </Button>
                  {connected && (
                    <Button size="sm" variant="ghost" onClick={() => syncOne(c)} disabled={c.id === 'onedrive' && odSyncing} title="Sync now">
                      <RefreshCw className={`h-4 w-4 ${c.id === 'onedrive' && odSyncing ? 'animate-spin' : ''}`} />
                    </Button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Uploaded files */}
      <Card padding={false}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-navy-700" />
            <h2 className="text-base font-semibold text-slate-900">Uploaded Files</h2>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
              {selectedIds.size > 0 ? `${selectedIds.size} / ${filteredFiles.length}` : filteredFiles.length}
            </span>
          </div>
          <div className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={fileSearch}
                onChange={(e) => setFileSearch(e.target.value)}
                placeholder="Search files…"
                className="w-40 rounded-lg border border-slate-200 bg-slate-50 py-1.5 pl-8 pr-2 text-xs outline-none focus:border-navy-400"
              />
            </div>
            {selectedIds.size > 0 && (
              <Button size="sm" variant="dangerOutline" onClick={deleteSelected}>
                <Trash2 className="h-3.5 w-3.5" /> Delete {selectedIds.size}
              </Button>
            )}
            <Button size="sm" onClick={() => setUploadOpen(true)}>
              <Upload className="h-3.5 w-3.5" /> Upload
            </Button>
          </div>
        </div>
        {filesLoading ? (
          <div className="px-5 py-8 text-center text-sm text-slate-400">Loading files…</div>
        ) : files.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-slate-400">No files uploaded. Click Upload to add documents.</div>
        ) : filteredFiles.length === 0 ? (
          <div className="px-5 py-8 text-center text-sm text-slate-400">No files match “{fileSearch}”.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead>
                <tr className="border-t border-slate-100 bg-slate-50/60 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  <th className="w-10 px-2 py-2.5 text-center">
                    <input type="checkbox" checked={selectedIds.size === filteredFiles.length && filteredFiles.length > 0} onChange={toggleSelectAll} className="h-4 w-4 rounded border-slate-300" />
                  </th>
                  <th className="px-2 py-2.5">Name</th>
                  <th className="px-3 py-2.5">Department</th>
                  <th className="px-5 py-2.5">Uploaded</th>
                  <th className="px-3 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {filteredFiles.map((f) => {
                  const badge = deptBadge(f.department)
                  return (
                    <tr key={f.id} className={`hover:bg-slate-50/80 ${selectedIds.has(f.id) ? 'bg-navy-50/40' : ''}`}>
                      <td className="w-10 px-2 py-3 text-center">
                        <input type="checkbox" checked={selectedIds.has(f.id)} onChange={() => toggleSelect(f.id)} className="h-4 w-4 rounded border-slate-300" />
                      </td>
                      <td className="max-w-[320px] truncate px-2 py-3 font-medium text-slate-800" title={f.name}>{f.name}</td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: badge.bg, color: badge.text }}>{badge.label}</span>
                      </td>
                      <td className="px-5 py-3 text-xs text-slate-500">{fmtDate(f.uploaded_at)}</td>
                      <td className="px-3 py-3">
                        <button type="button" onClick={() => handleDelete(f.id)} className="text-slate-400 hover:text-danger-500" title="Delete">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Roles summary */}
      <Card padding={false}>
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-navy-700" />
            <h2 className="text-base font-semibold text-slate-900">Roles & Access</h2>
          </div>
          <Button size="sm" variant="secondary" onClick={() => navigate('/admin/roles')}>
            <Settings className="h-3.5 w-3.5" /> Configure
          </Button>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {SEED_ROLES.map((r) => (
            <button key={r.id} type="button" onClick={() => navigate('/admin/roles')}
              className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 text-left transition hover:border-navy-200 hover:bg-white"
            >
              <p className="text-sm font-semibold text-slate-900">{r.name}</p>
              <p className="mt-1 text-2xl font-bold text-navy-800">{r.users}</p>
              <p className="text-[11px] text-slate-400">users</p>
              <p className="mt-2 text-xs text-slate-500">{r.permissions}</p>
            </button>
          ))}
        </div>
      </Card>

      <Modal open={!!manageConn} onClose={handleManageClose} title={manageConn ? `Manage ${manageConn.name}` : ''}
        footer={
          <>
            <Button variant="secondary" onClick={() => setManageConn(null)}>Close</Button>
            {manageConn?.status === 'Connected' && (
              <>
                <Button variant="secondary" onClick={() => syncOne(manageConn)}><RefreshCw className="h-4 w-4" /> Sync now</Button>
                <Button variant="dangerOutline" onClick={() => disconnect(manageConn)}>Disconnect</Button>
              </>
            )}
          </>
        }
      >
        {manageConn && (
          <div className="space-y-3 text-sm text-slate-600">
            <p>Status: <StatusBadge status={manageConn.status} /></p>
            <p>Last sync: {manageConn.lastSync || '—'}</p>
            <p className="text-xs text-slate-400">Prototype connection — no real OAuth. In production this would open the provider consent screen and list shared drives.</p>
          </div>
        )}
      </Modal>

      <Modal open={uploadOpen} onClose={handleUploadClose} title="Upload files">
        <FileUpload onUploaded={(name) => toast(`Uploaded ${name}`, 'success')} onClose={handleUploadClose} />
      </Modal>
    </div>
  )
}
