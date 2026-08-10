import { useState, useEffect } from 'react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Section from '../components/ui/Section'
import Modal from '../components/ui/Modal'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

export default function Workflows() {
  const { toast } = useApp()
  const [workflows, setWorkflows] = useState([])
  const [active, setActive] = useState(null)
  const [loading, setLoading] = useState(true)
  const [configIndex, setConfigIndex] = useState(null)
  const [stageName, setStageName] = useState('')
  const [instances, setInstances] = useState([])
  const [startOpen, setStartOpen] = useState(false)
  const [startTitle, setStartTitle] = useState('')

  useEffect(() => {
    api('/api/workflows')
      .then((data) => {
        const list = data.workflows || []
        setWorkflows(list)
        setActive(list[0] || null)
      })
      .catch(() => toast('Could not load workflows', 'error'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!active) return
    api(`/api/workflows/${active.id}/instances`)
      .then((data) => setInstances(data.instances || []))
      .catch(() => setInstances([]))
  }, [active])

  function replace(workflow) {
    setWorkflows((ws) => ws.map((w) => (w.id === workflow.id ? workflow : w)))
    setActive(workflow)
  }

  async function publish() {
    if (!active) return
    try {
      const { workflow } = await api(`/api/workflows/${active.id}/publish`, { method: 'POST' })
      replace(workflow)
      toast(`Workflow “${workflow.name}” published`, 'success')
    } catch {
      toast('Publish failed', 'error')
    }
  }

  async function addStage() {
    if (!active) return
    try {
      const { workflow } = await api(`/api/workflows/${active.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ stages: [...active.stages, 'New Stage'] }),
      })
      replace(workflow)
    } catch {
      toast('Could not add stage', 'error')
    }
  }

  function openConfig(index) {
    setConfigIndex(index)
    setStageName(active.stages[index])
  }

  async function saveStage() {
    const i = configIndex
    const name = stageName.trim()
    const stages = active.stages.map((s, idx) => (idx === i ? (name || s) : s))
    try {
      const { workflow } = await api(`/api/workflows/${active.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ stages }),
      })
      replace(workflow)
      setConfigIndex(null)
      toast('Stage updated', 'success')
    } catch {
      toast('Could not update stage', 'error')
    }
  }

  async function removeStage() {
    const i = configIndex
    const stages = active.stages.filter((_, idx) => idx !== i)
    try {
      const { workflow } = await api(`/api/workflows/${active.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ stages }),
      })
      replace(workflow)
      setConfigIndex(null)
      toast('Stage removed', 'success')
    } catch {
      toast('Could not remove stage', 'error')
    }
  }

  async function startRequest() {
    const title = startTitle.trim() || `New request ${new Date().toLocaleDateString()}`
    try {
      await api(`/api/workflows/${active.id}/start`, {
        method: 'POST',
        body: JSON.stringify({ title }),
      })
      setStartOpen(false)
      setStartTitle('')
      const { instances: list } = await api(`/api/workflows/${active.id}/instances`)
      setInstances(list)
      toast('Request started', 'success')
    } catch {
      toast('Could not start request', 'error')
    }
  }

  async function advance(id) {
    try {
      await api(`/api/workflows/instances/${id}/advance`, { method: 'POST' })
      const { instances: list } = await api(`/api/workflows/${active.id}/instances`)
      setInstances(list)
    } catch {
      toast('Could not advance request', 'error')
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl py-16 text-center">
        <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-navy-200 border-t-navy-700" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Workflow Builder"
        subtitle="Visual no-code automation for admission, leave, purchase, recruitment, and more."
        actions={
          <Button size="sm" onClick={publish} disabled={!active || active.status === 'published'}>
            {active?.status === 'published' ? 'Published' : 'Publish workflow'}
          </Button>
        }
      />

      {!active ? (
        <Card className="p-10 text-center text-sm text-slate-500">
          No workflows yet. Create one to get started.
        </Card>
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <div className="space-y-3 lg:col-span-3">
            {workflows.map((w) => (
              <button
                key={w.id}
                type="button"
                onClick={() => setActive(w)}
                className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                  active.id === w.id
                    ? 'border-navy-300 bg-navy-50 ring-1 ring-navy-100'
                    : 'border-slate-200 bg-white hover:border-slate-300'
                }`}
              >
                <p className="text-sm font-semibold text-slate-900">{w.name}</p>
                <p className="text-[11px] text-slate-400">
                  {w.stages.length} stages{w.status === 'published' ? ' · Published' : ' · Draft'}
                </p>
              </button>
            ))}
          </div>

          <div className="lg:col-span-9">
            <Section
              title={active.name}
              subtitle="Click a stage to rename it, or add new stages"
              action={
                <>
                  <Button size="sm" variant="secondary" onClick={addStage}>
                    + Add stage
                  </Button>
                  <Button size="sm" onClick={() => setStartOpen(true)} disabled={active.status !== 'published'}>
                    Start request
                  </Button>
                </>
              }
            >
              <div className="wf-grid min-h-[320px] rounded-2xl border border-slate-200 bg-white p-8">
                <div className="flex flex-wrap items-center justify-center gap-3">
                  {active.stages.map((stage, i) => (
                    <div key={`${stage}-${i}`} className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => openConfig(i)}
                        className="min-w-[100px] rounded-2xl border border-slate-200 bg-white px-4 py-4 text-center shadow-sm transition hover:shadow-md"
                        style={{ borderTopColor: active.color, borderTopWidth: 3 }}
                      >
                        <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                          Stage {i + 1}
                        </p>
                        <p className="mt-1 text-sm font-semibold text-slate-900">{stage}</p>
                      </button>
                      {i < active.stages.length - 1 && (
                        <div className="hidden h-px w-6 bg-slate-300 sm:block" />
                      )}
                    </div>
                  ))}
                </div>
                <p className="mt-10 text-center text-xs text-slate-400">
                  Click a stage to rename it. Publish to lock the workflow.
                </p>
              </div>
            </Section>

            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Card>
                <p className="text-xs text-slate-400">Trigger</p>
                <p className="mt-1 text-sm font-semibold">Form submit / API / Schedule</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Human gate</p>
                <p className="mt-1 text-sm font-semibold">Principal / HOD approval</p>
              </Card>
              <Card>
                <p className="text-xs text-slate-400">Outcomes</p>
                <p className="mt-1 text-sm font-semibold">Notify · Update record · Memory</p>
              </Card>
            </div>

            <Section
              className="mt-4"
              title="Running requests"
              subtitle={`${instances.filter((i) => i.status === 'open').length} in progress`}
            >
              {instances.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-400">
                  No requests yet. Publish the workflow and start one.
                </p>
              ) : (
                <ul className="divide-y divide-slate-50">
                  {instances.map((inst) => (
                    <li key={inst.id} className="flex flex-wrap items-center gap-3 py-3">
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-medium ${inst.status === 'done' ? 'text-slate-400 line-through' : 'text-slate-800'}`}>
                          {inst.title}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          Stage {Math.min(inst.current_stage + 1, inst.total_stages)} of {inst.total_stages} · {inst.current_stage_name}
                        </p>
                      </div>
                      <span
                        className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${
                          inst.status === 'done'
                            ? 'border-success-100 bg-success-50 text-success-700'
                            : inst.status === 'open'
                              ? 'border-navy-100 bg-navy-50 text-navy-700'
                              : 'border-slate-200 bg-slate-100 text-slate-600'
                        }`}
                      >
                        {inst.status}
                      </span>
                      {inst.status === 'open' && (
                        <Button size="sm" variant="secondary" onClick={() => advance(inst.id)}>
                          Advance
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </Section>
          </div>
        </div>
      )}

      <Modal
        open={configIndex !== null}
        onClose={() => setConfigIndex(null)}
        title={`Configure stage ${(configIndex ?? 0) + 1}`}
        size="sm"
        footer={
          <>
            <button
              type="button"
              onClick={removeStage}
              className="mr-auto text-sm font-medium text-red-600 hover:text-red-700"
            >
              Remove stage
            </button>
            <Button size="sm" onClick={saveStage}>
              Save
            </Button>
          </>
        }
      >
        <label className="block text-xs font-medium text-slate-600">Stage name</label>
        <input
          value={stageName}
          onChange={(e) => setStageName(e.target.value)}
          autoFocus
          className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
        />
        <p className="mt-3 text-xs text-slate-400">
          Conditions, assignees, and SLAs for each stage can be configured here.
        </p>
      </Modal>

      <Modal
        open={startOpen}
        onClose={() => setStartOpen(false)}
        title={`Start request · ${active?.name ?? ''}`}
        size="sm"
        footer={
          <>
            <Button size="sm" variant="secondary" onClick={() => setStartOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={startRequest}>
              Start
            </Button>
          </>
        }
      >
        <label className="block text-xs font-medium text-slate-600">Request title</label>
        <input
          value={startTitle}
          onChange={(e) => setStartTitle(e.target.value)}
          autoFocus
          placeholder="e.g. Annual Day catering vendor"
          className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
        />
      </Modal>
    </div>
  )
}
