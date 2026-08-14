import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  MessageSquare,
  GraduationCap,
  Users,
  Wallet,
  Building2,
  Send,
  Sparkles,
  FileText,
  Plus,
  ChevronRight,
  Trash2,
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'

const chatDepartments = [
  { id: 'general', label: 'General', icon: 'MessageSquare' },
  { id: 'academic', label: 'Academic', icon: 'GraduationCap' },
  { id: 'hr', label: 'HR', icon: 'Users' },
  { id: 'finance', label: 'Finance', icon: 'Wallet' },
  { id: 'admin', label: 'Admin', icon: 'Building2' },
]

const suggestedFollowUps = [
  'What is the process for applying for maternity leave?',
  'Who approves leave for Heads of Department?',
  'Is half-day casual leave allowed?',
]

const deptIcons = {
  MessageSquare,
  GraduationCap,
  Users,
  Wallet,
  Building2,
}

const agentDeptMap = {
  principal: 'admin',
  teacher: 'academic',
  finance: 'finance',
  admissions: 'admin',
  hr: 'hr',
  compliance: 'admin',
  library: 'general',
  success: 'academic',
}

export default function AIChat() {
  const location = useLocation()
  const navigate = useNavigate()
  const { dispatch, toast, user, activeAgent } = useApp()
  const [activeDept, setActiveDept] = useState(activeAgent ? (agentDeptMap[activeAgent.id] || 'general') : 'hr')
  const [activeConv, setActiveConv] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  useEffect(() => {
    if (activeAgent) {
      setActiveDept(agentDeptMap[activeAgent.id] || 'general')
    }
  }, [activeAgent])

  const seededRef = useRef(null)
  useEffect(() => {
    const seed = location.state?.seedQuestion
    if (seed && seededRef.current !== seed) {
      seededRef.current = seed
      handleSend(seed)
    }
  }, [location.state])

  useEffect(() => {
    api('/api/chat/sessions')
      .then((data) => {
        setSessions(data.sessions || [])
        if (data.sessions?.length > 0) {
          setActiveConv(data.sessions[0].session_id)
          setSessionId(data.sessions[0].session_id)
          return api(`/api/chat/session?session_id=${data.sessions[0].session_id}`)
        }
        return null
      })
      .then((data) => {
        if (data?.messages?.length > 0) {
          setMessages(data.messages.map((m) => ({
            id: m.message_id,
            role: m.role,
            content: m.content,
            sources: m.sources || [],
          })))
        }
      })
      .catch(() => {})
  }, [])

  function clearAgent() {
    dispatch({ type: 'SET_ACTIVE_AGENT', payload: null })
  }

  const sourcesUsed = messages
    .filter((m) => m.role === 'assistant' && m.sources?.length)
    .flatMap((m) => m.sources)
    .filter((c, i, arr) => arr.findIndex((x) => (x.id || x.file_id) === (c.id || c.file_id)) === i)

  function openSource(s) {
    toast(`Viewing ${s.name || s.source || 'citation'}`, 'info')
    navigate(`/document/${s.file_id || s.id || ''}`, {
      state: {
        doc: {
          id: s.file_id || s.id,
          title: s.name || s.source,
          department: s.source,
          status: 'Current',
          snippet: s.text || s.excerpt || '',
        },
      },
    })
  }

  function appendReply(result) {
    setMessages((prev) => [...prev, {
      id: result.message_id || Date.now() + 1,
      role: 'assistant',
      content: result.response || '',
      sources: result.sources || [],
      suggestions: result.suggestions || [],
    }])
  }

  async function streamChat(content) {
    const tempId = Date.now() + 1
    setMessages((prev) => [...prev, { id: tempId, role: 'assistant', content: '', sources: [], suggestions: [] }])

    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ question: content, session_id: sessionId, department: activeDept, agent_scope: agentScope }),
    })

    const isSse = (res.headers.get('content-type') || '').includes('text/event-stream')
    if (!isSse || !res.body) {
      const data = await res.json().catch(() => ({}))
      setMessages((prev) => prev.map((m) => (m.id === tempId
        ? { ...m, content: data.response || data.error || 'Sorry, I encountered an error. Please try again.' }
        : m)))
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const patch = (fn) => setMessages((prev) => prev.map((m) => (m.id === tempId ? fn(m) : m)))

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop()
      for (const block of blocks) {
        const event = /^event: (.+)$/m.exec(block)?.[1]
        const dataLine = /^data: (.+)$/m.exec(block)?.[1]
        if (!dataLine) continue
        if (event === 'token') {
          let t = dataLine
          try { t = JSON.parse(dataLine) } catch { /* raw token */ }
          patch((m) => ({ ...m, content: m.content + t }))
        } else if (event === 'done') {
          let d = {}
          try { d = JSON.parse(dataLine) } catch { /* ignore */ }
          patch((m) => ({
            ...m,
            id: d.message_id || m.id,
            content: d.response ?? m.content,
            sources: d.sources || [],
            suggestions: d.suggestions || [],
          }))
        } else if (event === 'error') {
          let d = {}
          try { d = JSON.parse(dataLine) } catch { /* ignore */ }
          toast(d.message || 'Streaming failed', 'error')
        }
      }
    }
  }

  async function handleSend(text) {
    const content = (text ?? input).trim()
    if (!content) return
    setInput('')
    setMessages((prev) => [...prev, { id: Date.now(), role: 'user', content }])
    setIsTyping(true)

    const agentScope = activeAgent ? `${activeAgent.name}: ${activeAgent.scope}` : undefined
    try {
      if (agentScope) {
        const result = await api('/api/chat', {
          method: 'POST',
          body: JSON.stringify({
            question: content,
            session_id: sessionId,
            department: activeDept,
            agent_scope: agentScope,
          }),
        })
        appendReply(result)
      } else {
        await streamChat(content)
      }
      dispatch({
        type: 'ADD_ACTIVITY',
        payload: {
          id: Date.now(),
          user: user?.name || 'User',
          action: 'Asked AI',
          target: content.slice(0, 48) + (content.length > 48 ? '\u2026' : ''),
          time: 'Just now',
          type: 'chat',
        },
      })
    } catch (err) {
      toast(err.message || 'Chat failed', 'error')
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }])
    } finally {
      setIsTyping(false)
    }
  }

  function newChat() {
    setMessages([])
    setActiveConv(null)
    api('/api/chat/sessions', { method: 'POST', body: '{}' })
      .then((data) => {
        setSessionId(data.session.session_id)
        setSessions((prev) => [data.session, ...prev])
        toast('Started a new conversation', 'info')
      })
      .catch(() => toast('Could not create session', 'error'))
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-7.5rem)] max-w-7xl flex-col">
      <div className="mb-4 shrink-0 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">AI Chat</h1>
          <p className="mt-1 text-sm text-slate-500">
            Ask anything about school knowledge \u2014 answers always include citations
          </p>
        </div>
        <Button size="sm" variant="secondary" onClick={newChat}>
          <Plus className="h-4 w-4" /> New chat
        </Button>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-12">
        <aside className="flex min-h-0 flex-col gap-3 lg:col-span-3">
          <Card className="shrink-0 !p-3">
            <p className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              Department
            </p>
            <div className="space-y-0.5">
              {chatDepartments.map((d) => {
                const Icon = deptIcons[d.icon] || MessageSquare
                return (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => {
                      setActiveDept(d.id)
                      if (activeAgent) dispatch({ type: 'SET_ACTIVE_AGENT', payload: null })
                      toast(`Context: ${d.label}`, 'info')
                    }}
                    className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium transition ${
                      activeDept === d.id
                        ? 'bg-navy-900 text-white'
                        : 'text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {d.label}
                  </button>
                )
              })}
            </div>
          </Card>

          <Card className="flex min-h-0 flex-1 flex-col !p-0 overflow-hidden">
            <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2.5">
              <p className="text-xs font-semibold text-slate-700">Conversations</p>
              <button
                type="button"
                onClick={newChat}
                className="rounded-md p-1 text-navy-600 hover:bg-navy-50"
                title="New chat"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
            <ul className="flex-1 overflow-y-auto p-2">
              {sessions.map((s) => (
                <li key={s.session_id} className="group relative">
                  <button
                    type="button"
                    onClick={() => {
                      setActiveConv(s.session_id)
                      setSessionId(s.session_id)
                      api(`/api/chat/session?session_id=${s.session_id}`)
                        .then((data) => {
                          if (data?.messages?.length > 0) {
                            setMessages(data.messages.map((m) => ({
                              id: m.message_id,
                              role: m.role,
                              content: m.content,
                              sources: m.sources || [],
                            })))
                          } else {
                            setMessages([])
                          }
                        })
                        .catch(() => setMessages([]))
                    }}
                    className={`w-full rounded-lg px-2.5 py-2.5 text-left transition ${
                      activeConv === s.session_id ? 'bg-navy-50' : 'hover:bg-slate-50'
                    }`}
                  >
                    <p className="truncate text-sm font-medium text-slate-800">{s.title}</p>
                    <p className="mt-0.5 truncate text-[11px] text-slate-400">
                      {new Date(s.created_at * 1000).toLocaleDateString()}
                    </p>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      const next = sessions.filter((x) => x.session_id !== s.session_id)
                      setSessions(next)
                      if (activeConv === s.session_id) {
                        if (next.length > 0) {
                          setActiveConv(next[0].session_id)
                          setSessionId(next[0].session_id)
                        } else {
                          setActiveConv(null)
                          setSessionId(null)
                          setMessages([])
                        }
                      }
                      api(`/api/chat/sessions/${s.session_id}`, { method: 'DELETE' })
                        .then((data) => {
                          if (data?.sessions) setSessions(data.sessions)
                          if (data?.current_session_id) {
                            setActiveConv(data.current_session_id)
                            setSessionId(data.current_session_id)
                          }
                        })
                        .catch(() => toast('Failed to delete session', 'error'))
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-500"
                    title="Delete conversation"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </aside>

        <div className="flex min-h-0 flex-col rounded-xl border border-slate-200/80 bg-white shadow-sm lg:col-span-6">
          <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
            <div className="flex items-center gap-2">
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg text-white"
                style={{ backgroundColor: activeAgent?.color || '#1e3a5f' }}
              >
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  {activeAgent?.name || 'CEAP Assistant'}
                </p>
                <p className="text-[11px] text-slate-400">
                  {activeAgent
                    ? activeAgent.scope
                    : `Context: ${chatDepartments.find((d) => d.id === activeDept)?.label || 'General'} knowledge`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {activeAgent && (
                <button
                  type="button"
                  onClick={clearAgent}
                  className="rounded-lg px-2 py-1 text-[11px] font-medium text-navy-600 hover:bg-navy-50"
                  title="Clear agent context"
                >
                  General
                </button>
              )}
              <button
                type="button"
                onClick={() => {
                  setMessages([])
                  toast('Conversation cleared', 'info')
                }}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-600"
                title="Clear messages"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 space-y-5 overflow-y-auto px-4 py-5">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <Sparkles className="h-10 w-10 text-navy-200" />
                <p className="mt-3 text-sm font-medium text-slate-700">Start a conversation</p>
                <p className="mt-1 max-w-xs text-xs text-slate-400">
                  Ask about policies, leave rules, fees, compliance requirements, and more.
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  {suggestedFollowUps.slice(0, 2).map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => handleSend(q)}
                      className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-600 hover:border-navy-300 hover:bg-navy-50"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[90%] ${
                    msg.role === 'user'
                      ? 'rounded-2xl rounded-br-md bg-navy-900 px-4 py-2.5 text-sm text-white'
                      : 'space-y-3'
                  }`}
                >
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <>
                      <div className="rounded-2xl rounded-bl-md border border-slate-100 bg-slate-50 px-4 py-3 text-sm leading-relaxed text-slate-700">
                        <MessageBody text={msg.content} />
                      </div>
                      {msg.suggestions?.length > 0 && (
                        <div className="flex flex-wrap gap-2 pl-1">
                          {msg.suggestions.map((q, i) => (
                            <button
                              key={i}
                              type="button"
                              disabled={isTyping}
                              onClick={() => handleSend(q)}
                              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-navy-300 hover:bg-navy-50 disabled:opacity-50"
                            >
                              {q}
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Sparkles className="h-4 w-4 animate-pulse text-navy-400" />
                CEAP is thinking\u2026
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-slate-100 p-3">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSend()
              }}
              className="flex items-end gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask anything about school knowledge..."
                className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
              />
              <button
                type="submit"
                disabled={!input.trim() || isTyping}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </form>
          </div>
        </div>

        <aside className="flex min-h-0 flex-col gap-3 lg:col-span-3">
          <Card className="min-h-0 flex-1 overflow-y-auto">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900">
              <FileText className="h-4 w-4 text-navy-600" />
              Sources used
            </h3>
            <p className="mt-1 text-[11px] text-slate-400">
              Documents cited in this conversation
            </p>
            <ul className="mt-3 space-y-2">
              {sourcesUsed.length === 0 && (
                <li className="text-xs text-slate-400">No sources yet</li>
              )}
              {sourcesUsed.map((s, i) => (
                <li key={`${s.file_id || ''}-${s.chunk_index ?? i}`}>
                  <button
                    type="button"
                    onClick={() => openSource(s)}
                    className="w-full rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-left hover:border-navy-200"
                  >
                    <p className="text-xs font-semibold text-slate-800">{s.name || s.source}</p>
                    <p className="text-[10px] text-navy-600">{s.source}</p>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-slate-900">Suggested follow-ups</h3>
            <ul className="mt-3 space-y-1.5">
              {suggestedFollowUps.map((q) => (
                <li key={q}>
                  <button
                    type="button"
                    onClick={() => handleSend(q)}
                    disabled={isTyping}
                    className="flex w-full items-start gap-2 rounded-lg border border-slate-100 px-2.5 py-2 text-left text-xs text-slate-600 transition hover:border-navy-200 hover:bg-navy-50 hover:text-navy-800 disabled:opacity-50"
                  >
                    <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-navy-400" />
                    {q}
                  </button>
                </li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>
    </div>
  )
}

function MessageBody({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return (
    <div className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return (
            <strong key={i} className="font-semibold text-slate-900">
              {part.slice(2, -2)}
            </strong>
          )
        }
        return <span key={i}>{part}</span>
      })}
    </div>
  )
}
