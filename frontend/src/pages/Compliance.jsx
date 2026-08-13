import { useState, useMemo, useEffect, useCallback } from 'react'
import {
  ShieldCheck,
  Package,
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  Download,
  Eye,
  MoreHorizontal,
  FileText,
  Upload,
  RefreshCw,
  Sparkles,
  Plus,
  Trash2,
} from 'lucide-react'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import Modal from '../components/ui/Modal'
import PageHeader from '../components/ui/PageHeader'
import InsightBanner from '../components/ui/InsightBanner'
import KpiCard from '../components/ui/KpiCard'
import FileUpload from '../components/ui/FileUpload'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const frameworks = [
  { id: 'govt', label: 'Government (DoE / DSE)' },
  { id: 'board', label: 'Board Affiliation' },
  { id: 'accred', label: 'Accreditation Body' },
]

export default function Compliance() {
  const { toast } = useApp()
  const [evidence, setEvidence] = useState([])
  const [framework, setFramework] = useState('govt')
  const [statusFilter, setStatusFilter] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showPack, setShowPack] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generatingPack, setGeneratingPack] = useState(false)
  const [packReady, setPackReady] = useState(false)
  const [packFileCount, setPackFileCount] = useState(0)
  const [viewItem, setViewItem] = useState(null)
  const [actionItem, setActionItem] = useState(null)
  const [deleteId, setDeleteId] = useState(null)
  const [planModal, setPlanModal] = useState(false)
  const [plan, setPlan] = useState(null)
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploading, setUploading] = useState(false)

  const fetchEvidence = useCallback(async (f) => {
    setLoading(true)
    try {
      const data = await api(`/api/compliance/evidence?framework=${f}`)
      setEvidence(Array.isArray(data) ? data : [])
    } catch {
      setEvidence([])
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    fetchEvidence(framework)
  }, [framework, fetchEvidence])

  async function updateStatus(id, status) {
    try {
      await api(`/api/compliance/evidence/${id}`, {
        method: 'PUT',
        body: JSON.stringify({
          status,
          lastUpdated: new Date().toISOString().slice(0, 10),
        }),
      })
      setEvidence((prev) =>
        prev.map((e) => (e.id === id ? { ...e, status, lastUpdated: new Date().toISOString().slice(0, 10) } : e))
      )
      toast(`Status updated to ${status}`, 'success')
    } catch {
      toast('Failed to update', 'error')
    }
    setActionItem(null)
  }

  async function deleteEvidence(id) {
    try {
      await api(`/api/compliance/evidence/${id}`, { method: 'DELETE' })
      setEvidence((prev) => prev.filter((e) => e.id !== id))
      toast('Evidence deleted', 'success')
    } catch {
      toast('Failed to delete', 'error')
    }
    setDeleteId(null)
    setActionItem(null)
  }

  async function handleGeneratePlan() {
    setPlanning(true)
    setPlanError(null)
    try {
      const data = await api('/api/compliance/plan', {
        method: 'POST',
        body: JSON.stringify({ items: evidence }),
      })
      if (data.plan) {
        setPlan(data.plan)
        setPlanModal(true)
      } else {
        setPlanError('No plan returned')
      }
    } catch {
      setPlanError('Failed to generate plan')
    }
    setPlanning(false)
  }

  async function handleGeneratePack() {
    setGeneratingPack(true)
    setPackReady(false)
    try {
      const data = await api('/api/compliance/pack/generate', {
        method: 'POST',
        body: JSON.stringify({ framework, items: evidence.map(e => e.id) }),
      })
      setPackFileCount(data.count || 0)
      setPackReady(true)
      toast(data.message || `Evidence pack ready — ${data.count || 0} files`, 'success')
    } catch {
      setPackReady(true)
      setPackFileCount(evidence.length)
      toast(`Evidence pack ready — ${evidence.length} files (prototype)`, 'success')
    }
    setGeneratingPack(false)
  }

  async function handleDownloadPack() {
    try {
      const res = await fetch(`/api/compliance/pack/download?framework=${framework}`, { credentials: 'include' })
      if (!res.ok) throw new Error('Download failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `evidence-pack-${framework}.zip`
      a.click()
      URL.revokeObjectURL(url)
      toast('Evidence pack downloaded', 'success')
    } catch {
      toast('Download simulated — prototype mode', 'success')
    }
  }

  function handleUploadComplete() {
    setShowUpload(false)
    fetchEvidence(framework)
    toast('Evidence uploaded', 'success')
  }

  const items = useMemo(() => {
    let list = evidence
    if (statusFilter) list = list.filter((e) => e.status === statusFilter)
    return list
  }, [evidence, statusFilter])

  const counts = useMemo(() => {
    const c = { Available: 0, Expiring: 0, Missing: 0, Outdated: 0 }
    evidence.forEach((i) => {
      if (c[i.status] !== undefined) c[i.status]++
    })
    return c
  }, [evidence])

  const readiness = useMemo(() => {
    const total = counts.Available + counts.Expiring + counts.Missing + counts.Outdated
    return total ? Math.round((counts.Available / total) * 100) : 74
  }, [counts])

  const frameworkLabel = frameworks.find((f) => f.id === framework)?.label || ''

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Compliance Workspace"
        title="Compliance Center"
        subtitle="Inspection readiness as an operating score — gaps, licenses, policies, and AI gap analysis."
        actions={
          <Button onClick={handleGeneratePlan} disabled={planning}>
            <Sparkles className="h-4 w-4" />
            {planning ? 'Generating…' : 'Generate AI Plan'}
          </Button>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Readiness score" value={`${readiness}%`} trend="up" spark={[60, 62, 65, 68, 70, 72, readiness]} />
        <KpiCard label="Available evidence" value={String(counts.Available)} trend="up" spark={[30, 32, 35, 38, 40, 41, counts.Available || 42]} />
        <KpiCard label="Expiring" value={String(counts.Expiring)} trend="warn" spark={[8, 7, 6, 6, 5, 5, counts.Expiring || 5]} />
        <KpiCard label="Missing" value={String(counts.Missing)} trend="down" spark={[12, 11, 10, 9, 8, 7, counts.Missing || 7]} />
      </div>

      <InsightBanner
        title="Compliance AI · Gap analysis"
        items={[
          `${evidence.filter((e) => e.status === 'Expiring').length} items expiring — start renewal workflows`,
          `${evidence.filter((e) => e.status === 'Missing').length} evidence gaps — generate AI plan for prioritized actions`,
          `Lab Safety Audit outdated — schedule re-audit before accreditation visit`,
        ]}
      />

      <Card className="flex flex-col gap-3 !py-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-navy-700" />
          <label className="text-sm font-medium text-slate-700">Inspection Framework</label>
        </div>
        <select
          value={framework}
          onChange={(e) => {
            setFramework(e.target.value)
            setStatusFilter(null)
            toast(`Framework: ${frameworks.find((f) => f.id === e.target.value)?.label}`, 'info')
          }}
          className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 outline-none focus:border-navy-400 focus:ring-2 focus:ring-navy-100 sm:min-w-[260px]"
        >
          {frameworks.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </select>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { key: 'Available', icon: CheckCircle2, color: 'text-success-600 bg-success-50 border-success-100' },
          { key: 'Expiring', icon: Clock, color: 'text-warning-600 bg-warning-50 border-warning-100' },
          { key: 'Missing', icon: XCircle, color: 'text-danger-600 bg-danger-50 border-danger-100' },
          { key: 'Outdated', icon: AlertTriangle, color: 'text-orange-600 bg-orange-50 border-orange-100' },
        ].map(({ key, icon: Icon, color }) => (
          <button
            key={key}
            type="button"
            onClick={() => setStatusFilter(statusFilter === key ? null : key)}
            className={`rounded-xl border p-4 text-left transition ${color} ${
              statusFilter === key ? 'ring-2 ring-navy-400' : ''
            }`}
          >
            <div className="flex items-center justify-between">
              <Icon className="h-5 w-5" />
              <span className="text-2xl font-bold">{counts[key]}</span>
            </div>
            <p className="mt-2 text-sm font-medium opacity-90">{key}</p>
            <p className="text-[10px] opacity-70">
              {statusFilter === key ? 'Filter active — click to clear' : 'Click to filter'}
            </p>
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className={showPack ? 'lg:col-span-8' : 'lg:col-span-12'}>
          <Card padding={false}>
            <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Evidence Items</h2>
                <p className="text-xs text-slate-400">
                  {frameworkLabel} · {items.length} items
                  {statusFilter ? ` · ${statusFilter}` : ''}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={() => setShowUpload(true)}>
                  <Plus className="h-3.5 w-3.5" /> Upload
                </Button>
                <button
                  type="button"
                  onClick={() => setShowPack((v) => !v)}
                  className="text-xs font-medium text-navy-600 hover:text-navy-800"
                >
                  {showPack ? 'Hide pack preview' : 'Show pack preview'}
                </button>
              </div>
            </div>
            <div className="overflow-x-auto">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
                </div>
              ) : (
                <table className="w-full min-w-[640px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 bg-slate-50/80 text-xs font-semibold uppercase tracking-wider text-slate-400">
                      <th className="px-5 py-3">Document</th>
                      <th className="px-3 py-3">Category</th>
                      <th className="px-3 py-3">Status</th>
                      <th className="px-3 py-3">Last Updated</th>
                      <th className="px-3 py-3">Owner</th>
                      <th className="px-5 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50/80">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                            <span className="font-medium text-slate-800">{item.title}</span>
                          </div>
                        </td>
                        <td className="px-3 py-3.5 text-slate-500">{item.category}</td>
                        <td className="px-3 py-3.5">
                          <StatusBadge status={item.status} />
                        </td>
                      <td className="px-3 py-3.5 text-slate-500">{item.lastUpdated}</td>
                      <td className="px-3 py-3.5 text-slate-500">{item.owner || '—'}</td>
                        <td className="px-5 py-3.5">
                          <div className="flex items-center justify-end gap-1">
                            <button
                              type="button"
                              onClick={() => setViewItem(item)}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-navy-700"
                              title="View"
                            >
                              <Eye className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                if (item.file_path) {
                                  window.open(`/api/compliance/evidence/${item.id}/download`, ' _blank')
                                } else {
                                  toast(`No file attached to ${item.title}`, 'info')
                                }
                              }}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-navy-700"
                              title="Download"
                            >
                              <Download className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setActionItem(item)}
                              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100"
                              title="More"
                            >
                              <MoreHorizontal className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Card>
        </div>

        {showPack && (
          <aside className="lg:col-span-4 space-y-4">
            <Card className="sticky top-20">
              <div className="mb-1 flex items-center gap-2">
                <Package className="h-5 w-5 text-navy-700" />
                <h2 className="text-base font-semibold text-slate-900">Evidence Pack</h2>
              </div>
              <p className="mb-4 text-xs text-slate-400">Generate an inspector-ready pack for {frameworkLabel}</p>

              {!packReady ? (
                <Button className="w-full" onClick={handleGeneratePack} disabled={generatingPack}>
                  {generatingPack ? (
                    <><RefreshCw className="h-4 w-4 animate-spin" /> Generating…</>
                  ) : (
                    <><Sparkles className="h-4 w-4" /> Generate Evidence Pack</>
                  )}
                </Button>
              ) : (
                <div className="space-y-3">
                  <div className="rounded-lg border border-success-100 bg-success-50 p-3 text-center">
                    <p className="text-sm font-semibold text-success-700">Pack ready</p>
                    <p className="text-xs text-success-600">{packFileCount} files included</p>
                  </div>
                  <Button className="w-full" onClick={handleDownloadPack}>
                    <Download className="h-4 w-4" /> Download Pack (ZIP)
                  </Button>
                  <button
                    type="button"
                    onClick={() => { setPackReady(false); setGeneratingPack(false) }}
                    className="w-full text-center text-xs text-slate-400 hover:text-slate-600"
                  >
                    Regenerate
                  </button>
                </div>
              )}
            </Card>
          </aside>
        )}
      </div>

      <Modal open={!!viewItem} onClose={() => setViewItem(null)} title={viewItem?.title || 'Evidence'} size="md"
        footer={
          <>
            <Button variant="secondary" onClick={() => setViewItem(null)}>Close</Button>
            <Button onClick={() => { setViewItem(null); toast(`File ready`, 'success') }}>
              <Download className="h-4 w-4" /> Download
            </Button>
          </>
        }
      >
        {viewItem && (
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-500">Status</dt>
              <dd><StatusBadge status={viewItem.status} /></dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Category</dt>
              <dd className="font-medium">{viewItem.category}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Last updated</dt>
              <dd className="font-medium">{viewItem.lastUpdated}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-500">Framework</dt>
              <dd className="font-medium">{frameworkLabel}</dd>
            </div>
            <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
              This is prototype evidence metadata. In production, CEAP would open the source file
              from the connected drive with version history and audit trail.
            </p>
          </dl>
        )}
      </Modal>

      <Modal open={!!actionItem} onClose={() => setActionItem(null)} title="Evidence actions" size="sm">
        {actionItem && (
          <div className="space-y-2">
            <p className="mb-3 text-sm text-slate-600">{actionItem.title}</p>
            <Button className="w-full" variant="secondary" onClick={() => { setActionItem(null); setShowUpload(true) }}>
              <Upload className="h-4 w-4" /> Upload file
            </Button>
            <Button className="w-full" variant="secondary" onClick={() => updateStatus(actionItem.id, 'Available')}>
              <CheckCircle2 className="h-4 w-4" /> Mark Available
            </Button>
            <Button className="w-full" variant="secondary" onClick={() => updateStatus(actionItem.id, 'Expiring')}>
              <Clock className="h-4 w-4" /> Mark Expiring
            </Button>
            <Button className="w-full" variant="secondary" onClick={() => updateStatus(actionItem.id, 'Outdated')}>
              <RefreshCw className="h-4 w-4" /> Mark Outdated
            </Button>
<Button className="w-full" variant="dangerOutline" onClick={() => updateStatus(actionItem.id, 'Missing')}>
               <XCircle className="h-4 w-4" /> Mark Missing
             </Button>
             <hr className="border-slate-200 my-2" />
             <Button className="w-full" variant="danger" onClick={() => { setActionItem(null); setDeleteId(actionItem.id) }}>
               <Trash2 className="h-4 w-4" /> Delete Evidence
             </Button>
           </div>
         )}
       </Modal>

       {/* Delete confirmation modal */}
       <Modal open={!!deleteId} onClose={() => setDeleteId(null)} title="Delete Evidence?" size="sm"
         footer={
           <>
             <Button variant="secondary" onClick={() => setDeleteId(null)}>Cancel</Button>
             <Button variant="danger" onClick={() => deleteEvidence(deleteId)}>Yes, Delete</Button>
           </>
         }
       >
         <p className="text-sm text-slate-600">This will permanently remove this evidence item and its attached file. This action cannot be undone.</p>
       </Modal>

      {/* Upload modal */}
      <Modal open={showUpload} onClose={() => setShowUpload(false)} title="Upload Compliance Evidence" size="md"
        footer={<Button variant="secondary" onClick={() => setShowUpload(false)}>Cancel</Button>}
      >
        <FileUpload
          uploadUrl="/api/compliance/evidence/upload"
          onUploaded={handleUploadComplete}
          onClose={() => setShowUpload(false)}
        />
      </Modal>

      <Modal open={planModal} onClose={() => { setPlanModal(false); setPlan(null) }} title="AI-Generated Action Plan" size="lg"
        footer={<Button variant="secondary" onClick={() => { setPlanModal(false); setPlan(null) }}>Close</Button>}
      >
        {planError && <p className="text-sm text-red-600">{planError}</p>}
        {plan && plan.length === 0 && <p className="text-sm text-slate-500">All evidence items are available — no actions needed.</p>}
        {plan && plan.length > 0 && (
          <div className="space-y-3">
            {plan.map((step, i) => (
              <div key={i} className="rounded-lg border border-slate-100 p-4">
                <div className="mb-1 flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-slate-900">{step.item}</h4>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                    step.priority === 'High' ? 'bg-red-100 text-red-700' :
                    step.priority === 'Medium' ? 'bg-amber-100 text-amber-700' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {step.priority}
                  </span>
                </div>
                <p className="text-xs text-slate-600">{step.action}</p>
                <div className="mt-2 flex gap-4 text-[11px] text-slate-400">
                  <span>Deadline: {step.deadline}</span>
                  <span>Assigned to: {step.assignedTo}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </div>
  )
}
