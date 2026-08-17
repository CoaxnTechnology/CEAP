import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles, X, Send, Square, ChevronRight } from 'lucide-react'
import { useApp } from '../../context/AppContext'
import { aiAgents } from '../../data/osData'
import { api } from '../../lib/api'
import Markdown from '../ui/Markdown'

const starters = [
  'What needs my attention this morning?',
  'Which students are high risk?',
  'Summarize fee outstanding',
  'Inspection readiness status?',
]

const agentDeptMap = {
  principal: 'executive',
  teacher: 'academic',
  finance: 'finance',
  admissions: 'admissions',
  hr: 'hr',
  compliance: 'compliance',
  library: 'knowledge',
  success: 'students',
}

export default function AICopilot({ open, onClose }) {
  const { user, toast } = useApp()
  const navigate = useNavigate()
  const [agent, setAgent] = useState('principal')
  const [input, setInput] = useState('')
  const [isStopping, setIsStopping] = useState(false)
  const abortRef = useRef(null)
  const [msgs, setMsgs] = useState([
    {
      role: 'assistant',
      text: `Hi ${user?.name?.split(' ')[0] || 'there'}. I’m your Principal AI — school-wide intelligence with citations. Ask about attendance, risk, fees, compliance, or approvals.`,
    },
  ])

  const current = aiAgents.find((a) => a.id === agent)

  function send(text) {
    const q = (text ?? input).trim()
    if (!q) return
    const a = current
    setMsgs((m) => [...m, { role: 'user', text: q }])
    setMsgs((m) => [...m, { role: 'assistant', text: '…' }])
    setInput('')
    setIsStopping(true)
    abortRef.current = new AbortController()
    api('/api/chat', {
      method: 'POST',
      signal: abortRef.current.signal,
      body: JSON.stringify({
        question: q,
        want_suggestions: false,
        department: agentDeptMap[a.id] || 'general',
        agent_scope: a ? `${a.name}: ${a.scope}` : undefined,
      }),
    })
      .then((res) => {
        setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', text: res.response || res.answer || 'No response.' }])
      })
      .catch((err) => {
        if (err.name === 'AbortError') {
          setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', text: 'Response stopped.' }])
        } else {
          setMsgs((m) => [...m.slice(0, -1), { role: 'assistant', text: err.message || 'Chat failed. Try again.' }])
        }
      })
      .finally(() => {
        setIsStopping(false)
        abortRef.current = null
      })
  }

  function stop() {
    abortRef.current?.abort()
  }

  if (!open) return null

  return (
    <div className="fixed bottom-0 right-0 top-0 z-[80] flex w-full max-w-md flex-col border-l border-slate-200 bg-white shadow-2xl sm:bottom-4 sm:right-4 sm:top-4 sm:rounded-2xl sm:border">
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy-900 text-white">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">CEAP AI</p>
            <p className="text-[11px] text-slate-400">{current?.name} · {current?.permissions}</p>
          </div>
        </div>
        <button type="button" onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100">
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-slate-50 px-3 py-2">
        {aiAgents.slice(0, 5).map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => {
              setAgent(a.id)
              toast(`Switched to ${a.name}`, 'info')
            }}
            className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium ${
              agent === a.id ? 'bg-navy-900 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {a.name.replace(' AI', '')}
          </button>
        ))}
        <button
          type="button"
          onClick={() => {
            onClose()
            navigate('/ai')
          }}
          className="shrink-0 rounded-full px-2.5 py-1 text-[11px] font-medium text-navy-600 hover:bg-navy-50"
        >
          All agents →
        </button>
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'rounded-br-md bg-navy-900 text-white'
                  : 'rounded-bl-md border border-slate-100 bg-slate-50 text-slate-700'
              }`}
            >
              {m.role === 'user' ? m.text : <Markdown text={m.text} />}
            </div>
          </div>
        ))}
        {msgs.length === 1 && (
          <div className="space-y-1.5 pt-2">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Try asking</p>
            {starters.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="flex w-full items-center gap-2 rounded-xl border border-slate-100 px-3 py-2 text-left text-xs text-slate-600 hover:border-navy-200 hover:bg-navy-50"
              >
                <ChevronRight className="h-3 w-3 text-navy-400" />
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          if (isStopping) {
            stop()
          } else {
            send()
          }
        }}
        className="flex gap-2 border-t border-slate-100 p-3"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isStopping}
          placeholder="Ask anything about the school…"
          className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white disabled:opacity-60"
        />
        <button
          type="submit"
          title={isStopping ? 'Stop response' : 'Send'}
          className={`flex h-10 w-10 items-center justify-center rounded-xl text-white hover:bg-navy-800 ${
            isStopping ? 'bg-red-600 hover:bg-red-700' : 'bg-navy-900'
          }`}
        >
          {isStopping ? <Square className="h-3.5 w-3.5" /> : <Send className="h-4 w-4" />}
        </button>
      </form>
    </div>
  )
}
