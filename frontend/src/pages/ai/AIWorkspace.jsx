import { useNavigate } from 'react-router-dom'
import { Sparkles, MessageSquare, FilePenLine, Shield } from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import Button from '../../components/ui/Button'
import { aiAgents, docStudioTypes } from '../../data/osData'
import { useApp } from '../../context/AppContext'

export default function AIWorkspace() {
  const navigate = useNavigate()
  const { dispatch, toast } = useApp()

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <PageHeader
        eyebrow="AI Workspace"
        title="AI Studio"
        subtitle="Multi-agent intelligence with role-based permissions. AI drafts — humans approve."
        actions={
          <>
            <Button variant="secondary" size="sm" onClick={() => navigate('/ai/chat')}>
              <MessageSquare className="h-3.5 w-3.5" /> Chat
            </Button>
            <Button size="sm" onClick={() => navigate('/ai/studio')}>
              <FilePenLine className="h-3.5 w-3.5" /> Document Studio
            </Button>
          </>
        }
      />

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Multi AI Agents</h2>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {aiAgents.map((a) => (
            <Card
              key={a.id}
              className="card-hover relative overflow-hidden"
              onClick={() => {
                dispatch({ type: 'SET_ACTIVE_AGENT', payload: a })
                navigate('/ai/chat')
              }}
            >
              <div className="absolute left-0 top-0 h-1 w-full" style={{ backgroundColor: a.color }} />
              <div
                className="flex h-10 w-10 items-center justify-center rounded-xl text-white"
                style={{ backgroundColor: a.color }}
              >
                <Sparkles className="h-4 w-4" />
              </div>
              <h3 className="mt-3 font-semibold text-slate-900">{a.name}</h3>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">{a.scope}</p>
              <p className="mt-3 inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
                <Shield className="h-3 w-3" /> {a.permissions}
              </p>
            </Card>
          ))}
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-slate-800">Document Studio types</h2>
        <div className="flex flex-wrap gap-2">
          {docStudioTypes.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => navigate('/ai/studio')}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:border-navy-300 hover:bg-navy-50"
            >
              {t}
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-400">
          Every generation requires human approval before publish — AI never publishes alone.
        </p>
      </div>
    </div>
  )
}
