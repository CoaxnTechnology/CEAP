import { useEffect, useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import KpiCard from '../components/ui/KpiCard'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import InsightBanner from '../components/ui/InsightBanner'
import Modal from '../components/ui/Modal'
import WorkflowQuickStart from '../components/WorkflowQuickStart'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

export default function HR() {
  const { toast, dispatch } = useApp()
  const [data, setData] = useState(null)
  const [showReq, setShowReq] = useState(false)
  const [reqTitle, setReqTitle] = useState('')
  const [reqDept, setReqDept] = useState('')
  const [policies, setPolicies] = useState([])
  const [polCategories, setPolCategories] = useState(['leave'])
  const [showPolicy, setShowPolicy] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState(null)
  const [polName, setPolName] = useState('')
  const [polCategory, setPolCategory] = useState('leave')
  const [polContent, setPolContent] = useState('')
  const [extracting, setExtracting] = useState(false)

  function load() {
    return api('/api/hr/overview').then(setData)
  }

  function loadPolicies() {
    return api('/api/hr/policies').then((d) => {
      setPolicies(d.policies || [])
      setPolCategories(d.categories || ['leave'])
    })
  }

  useEffect(() => {
    load().catch(() => toast('Could not load HR data', 'warning'))
    loadPolicies().catch(() => {})
  }, [])

  function decide(id, decision, name) {
    api(`/api/hr/leave/${id}/decide`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: decision === 'approved' ? 'Approved leave for' : 'Rejected leave for',
            target: name,
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(res.message || `Leave ${decision}`, decision === 'approved' ? 'success' : 'warning')
        return load()
      })
      .catch(() => toast('Could not update leave request', 'warning'))
  }

  function createRequisition() {
    if (!reqTitle.trim()) {
      toast('Role title is required', 'warning')
      return
    }
    api('/api/hr/requisitions', {
      method: 'POST',
      body: JSON.stringify({ title: reqTitle.trim(), department: reqDept.trim() }),
    })
      .then((res) => {
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            id: Date.now(),
            user: 'You',
            action: 'Opened requisition for',
            target: res.title,
            time: 'Just now',
            type: 'approve',
          },
        })
        toast(res.message, 'success')
        setShowReq(false)
        setReqTitle('')
        setReqDept('')
        return load()
      })
      .catch(() => toast('Could not create requisition', 'warning'))
  }

  function openNewPolicy() {
    setEditingPolicy(null)
    setPolName('')
    setPolCategory('leave')
    setPolContent('')
    setShowPolicy(true)
  }

  function openEditPolicy(p) {
    setEditingPolicy(p)
    setPolName(p.name)
    setPolCategory(p.category || 'leave')
    setPolContent(p.content)
    setShowPolicy(true)
  }

  function savePolicy() {
    if (!polName.trim() || !polContent.trim()) {
      toast('Policy name and content are required', 'warning')
      return
    }
    setExtracting(true)
    const body = { name: polName, category: polCategory, content: polContent, active: true }
    const req = editingPolicy
      ? api(`/api/hr/policies/${editingPolicy.id}`, {
          method: 'PUT',
          body: JSON.stringify(body),
        })
      : api('/api/hr/policies', {
          method: 'POST',
          body: JSON.stringify(body),
        })
    req
      .then((res) => {
        toast(res.message, 'success')
        setShowPolicy(false)
        setExtracting(false)
        return Promise.all([loadPolicies(), load()])
      })
      .catch(() => {
        setExtracting(false)
        toast('Could not save policy', 'warning')
      })
  }

  if (!data) {
    return <div className="mx-auto max-w-7xl px-6 py-10 text-sm text-slate-400">Loading…</div>
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="HR Workspace"
        title="People Intelligence"
        subtitle="Workforce presence, leave, hiring — policies and approvals with HR AI."
        actions={
          <>
            <WorkflowQuickStart workflowKey="leave" label="Start leave" />
            <WorkflowQuickStart workflowKey="recruitment" label="Hiring" />
            <Button size="sm" onClick={() => setShowReq(true)}>
              New requisition
            </Button>
          </>
        }
      />

      <Modal
        open={showReq}
        onClose={() => setShowReq(false)}
        title="New job requisition"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setShowReq(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={createRequisition}>
              Open requisition
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Role title</label>
            <input
              type="text"
              value={reqTitle}
              onChange={(e) => setReqTitle(e.target.value)}
              placeholder="e.g. PGT Mathematics"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-300 focus:ring-2 focus:ring-navy-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Department</label>
            <input
              type="text"
              value={reqDept}
              onChange={(e) => setReqDept(e.target.value)}
              placeholder="e.g. Academic"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-300 focus:ring-2 focus:ring-navy-100"
            />
          </div>
        </div>
      </Modal>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Headcount" value={String(data.headcount)} spark={[80, 81, 82, 83, 84, 85, 85]} trend="up" delta="+2" />
        <KpiCard label="Present today" value={String(data.presentToday)} spark={[78, 80, 79, 81, 80, 82, 81]} trend="flat" delta={`${data.onLeave} leave`} />
        <KpiCard label="Open roles" value={String(data.openRoles)} spark={[5, 4, 4, 3, 3, 3, 3]} trend="warn" delta={data.openRoleName} />
        <KpiCard label="Training due" value={String(data.trainingDue)} spark={[10, 9, 8, 7, 7, 6, 6]} trend="warn" delta="Safeguarding" />
      </div>

      <InsightBanner title="HR AI" items={data.insights} />

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Workforce today" padding={false}>
          <ul className="divide-y divide-slate-50">
            {data.staff.map((s) => (
              <li key={s.id} className="flex items-center justify-between px-5 py-3.5">
                <div>
                  <p className="text-sm font-medium text-slate-800">{s.name}</p>
                  <p className="text-[11px] text-slate-400">
                    {s.role} · {s.dept}
                  </p>
                </div>
                <div className="text-right">
                  <StatusBadge status={s.status === 'Present' ? 'Current' : 'Expiring'} />
                  <p className="mt-1 text-[10px] text-slate-400">Leave bal {s.leaveBalance}d</p>
                </div>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Leave requests" padding={false}>
          <ul className="divide-y divide-slate-50">
            {data.leaveRequests.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-5 py-3.5">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800">{r.name}</p>
                  <p className="text-[11px] text-slate-400">
                    {r.type} · {r.dates}
                    {r.halfDay ? ' · Half day' : ''}
                  </p>
                </div>
                {r.status === 'pending' ? (
                  <div className="flex gap-1">
                    <Button size="sm" variant="success" onClick={() => decide(r.id, 'approved', r.name)}>
                      Approve
                    </Button>
                    <Button size="sm" variant="dangerOutline" onClick={() => decide(r.id, 'rejected', r.name)}>
                      Reject
                    </Button>
                  </div>
                ) : (
                  <StatusBadge status="Current" />
                )}
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <Section
        title="Policies"
        subtitle="Write any policy — HR AI extracts the rules (leave rules, attendance, conduct, etc.)."
        padding={false}
        action={
          <Button size="sm" variant="secondary" onClick={openNewPolicy}>
            + Add policy
          </Button>
        }
      >
        {policies.length === 0 ? (
          <p className="px-5 py-6 text-center text-sm text-slate-400">
            No policies yet. Add one and HR AI will generate the rules.
          </p>
        ) : (
          <ul className="divide-y divide-slate-50">
            {policies.map((p) => (
              <li key={p.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-800">
                    <span className="mr-2 rounded-full bg-navy-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-navy-600">
                      {p.category}
                    </span>
                    {p.name}
                    {p.active && (
                      <span className="ml-2 rounded-full bg-success-50 px-2 py-0.5 text-[10px] font-semibold text-success-600">
                        ACTIVE
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 text-[11px] text-slate-500">{p.rules?.summary || p.content}</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {p.rules?.summary ? 'AI summary' : ''}
                    {Object.keys(p.rules?.leave_types || {}).length
                      ? ` · ${Object.keys(p.rules.leave_types).length} leave types · ${
                          p.rules.approver_routing || '—'
                        } routing · ${p.rules.exclude_weekends ? 'weekends excluded' : 'weekends counted'}`
                      : ''}
                  </p>
                  {p.rules?.rules && Object.keys(p.rules.rules).length > 0 && (
                    <p className="mt-1 text-[11px] text-slate-400">
                      {Object.entries(p.rules.rules)
                        .slice(0, 3)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(' · ')}
                    </p>
                  )}
                </div>
                <Button size="sm" variant="secondary" onClick={() => openEditPolicy(p)}>
                  Edit
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Modal
        open={showPolicy}
        onClose={() => setShowPolicy(false)}
        title={editingPolicy ? `Edit policy: ${editingPolicy.name}` : 'Add policy'}
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setShowPolicy(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={savePolicy} disabled={extracting}>
              {extracting ? 'Extracting rules…' : editingPolicy ? 'Update policy' : 'Create policy'}
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Policy name</label>
            <input
              type="text"
              value={polName}
              onChange={(e) => setPolName(e.target.value)}
              placeholder="e.g. Staff Leave Policy 2026"
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-300 focus:ring-2 focus:ring-navy-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Category</label>
            <select
              value={polCategory}
              onChange={(e) => setPolCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-300 focus:ring-2 focus:ring-navy-100"
            >
              {polCategories.map((c) => (
                <option key={c} value={c}>
                  {c.charAt(0).toUpperCase() + c.slice(1)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">Policy content</label>
            <textarea
              rows="7"
              value={polContent}
              onChange={(e) => setPolContent(e.target.value)}
              placeholder="e.g. Annual leave is 20 days and cannot be taken as half days. Sick leave is 12 days and half days are allowed. Casual leave is 8 days. Weekends are not counted as leave days. Leave is approved by the department head."
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-navy-300 focus:ring-2 focus:ring-navy-100"
            />
          </div>
          <p className="text-[11px] text-slate-400">
            HR AI reads this text and extracts the rules — leave type caps, half-day allowance,
            approval routing, and weekend counting for leave policies; a summary and key rules for
            attendance, conduct, safety, and other policies.
          </p>
        </div>
      </Modal>
    </div>
  )
}
