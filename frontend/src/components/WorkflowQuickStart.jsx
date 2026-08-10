import { useEffect, useState } from 'react'
import Button from './ui/Button'
import Modal from './ui/Modal'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

export default function WorkflowQuickStart({ workflowKey, label, size = 'sm', variant = 'secondary' }) {
  const { toast } = useApp()
  const [workflow, setWorkflow] = useState(null)
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api('/api/workflows')
      .then((d) =>
        setWorkflow((d.workflows || []).find((w) => w.key === workflowKey && w.status === 'published'))
      )
      .catch(() => {})
  }, [workflowKey])

  async function start() {
    if (!workflow) return
    setBusy(true)
    try {
      await api(`/api/workflows/${workflow.id}/start`, {
        method: 'POST',
        body: JSON.stringify({ title: title.trim() || `${workflow.name} request` }),
      })
      setOpen(false)
      setTitle('')
      toast(`${workflow.name} started`, 'success')
    } catch {
      toast('Could not start workflow', 'error')
    } finally {
      setBusy(false)
    }
  }

  if (!workflow) return null

  return (
    <>
      <Button size={size} variant={variant} onClick={() => setOpen(true)}>
        {label || `Start ${workflow.name}`}
      </Button>
      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={`Start ${workflow.name}`}
        size="sm"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={start} disabled={busy}>
              {busy ? 'Starting…' : 'Start'}
            </Button>
          </>
        }
      >
        <label className="block text-xs font-medium text-slate-600">Request title</label>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          autoFocus
          placeholder="e.g. Leave for Pooja Iyer"
          className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
        />
      </Modal>
    </>
  )
}
