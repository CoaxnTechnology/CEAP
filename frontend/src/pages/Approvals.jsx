import { useEffect, useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import Section from '../components/ui/Section'
import StatusBadge from '../components/ui/StatusBadge'
import Button from '../components/ui/Button'
import { approvals as seed } from '../data/osData'
import { useApp } from '../context/AppContext'
import { api } from '../lib/api'

export default function Approvals() {
  const { toast, dispatch, user } = useApp()
  const [items, setItems] = useState(seed)

  useEffect(() => {
    api('/api/approvals')
      .then((r) => setItems(r.approvals))
      .catch(() => setItems(seed))
  }, [])

  async function decide(id, status) {
    const item = items.find((a) => a.id === id)
    try {
      await api(`/api/approvals/${id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: status.toLowerCase(), approver: user?.email || '' }),
      })
      setItems((list) => list.map((a) => (a.id === id ? { ...a, status, sla: 'Done' } : a)))
      dispatch({
        type: 'ADD_ACTIVITY',
        payload: {
          id: Date.now(),
          user: user?.name || 'You',
          action: status,
          target: item?.title || 'request',
          time: 'Just now',
          type: 'approve',
        },
      })
      toast(`${status}: ${item?.title}`, status === 'Approved' ? 'success' : 'warning')
    } catch {
      toast(`Could not ${status.toLowerCase()}: ${item?.title}`, 'error')
    }
  }

  const pending = items.filter((a) => a.status === 'Pending')

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Approvals"
        subtitle="Human-in-the-loop inbox — fee waivers, publishes, purchases, offers."
      />

      <Section title={`${pending.length} pending`} padding={false}>
        <ul className="divide-y divide-slate-50">
          {items.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-3 px-5 py-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-slate-900">{a.title}</p>
                <p className="text-[11px] text-slate-400">
                  {a.type} · {a.requester} · {a.amount} · {a.sla}
                </p>
              </div>
              <StatusBadge status={a.status === 'Approved' ? 'Current' : a.status === 'Rejected' ? 'Missing' : 'Expiring'} />
              {a.status === 'Pending' && (
                <div className="flex gap-1">
                  <Button size="sm" variant="success" onClick={() => decide(a.id, 'Approved')}>
                    Approve
                  </Button>
                  <Button size="sm" variant="dangerOutline" onClick={() => decide(a.id, 'Rejected')}>
                    Reject
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}