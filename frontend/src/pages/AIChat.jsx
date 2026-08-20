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
  Square,
} from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Markdown from '../components/ui/Markdown'
import { api } from '../lib/api'
import { useApp } from '../context/AppContext'
let uuidCounter = 0
let activeStreamSessionId = null
let streamPollTimer = null
let aiChatMounted = false

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
  const [activeDept, setActiveDept] = useState(activeAgent ? (agentDeptMap[activeAgent.id] || 'general') : 'general')
  const [activeConv, setActiveConv] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const abortRef = useRef(null)
  const messagesCacheRef = useRef({})
  const loadedForRef = useRef(null)
  const [sessionId, setSessionId] = useState(null)
  const [sessions, setSessions] = useState([])
  const bottomRef = useRef(null)
  const streamOwnerRef = useRef(false)
  const [indexedDocs, setIndexedDocs] = useState([])
  const [mentionIdx, setMentionIdx] = useState(0)
  const inputRef = useRef(null)
  const mentionListRef = useRef(null)

  useEffect(() => {
    aiChatMounted = true
    return () => { aiChatMounted = false }
  }, [])

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
    if (loadedForRef.current === sessionId && sessionId && activeStreamSessionId !== sessionId) {
      messagesCacheRef.current[sessionId] = messages
    }
  }, [messages, sessionId])

  useEffect(() => {
    api('/api/files')
      .then((data) => {
        const files = data.files || {}
        setIndexedDocs(
          Object.entries(files)
            .filter(([, f]) => f.indexed)
            .map(([file_id, f]) => ({ file_id, name: f.name || file_id }))
        )
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    api('/api/chat/sessions')
      .then((data) => {
        setSessions(data.sessions || [])
        if (data.sessions?.length > 0) {
          setActiveConv(data.sessions[0].session_id)
          setSessionId(data.sessions[0].session_id)
          return loadMessages(data.sessions[0].session_id)
        }
        return null
      })
      .catch(() => {})
  }, [])

  function loadMessages(sessionId) {
    const streaming = activeStreamSessionId === sessionId
    const cached = messagesCacheRef.current[sessionId]
    if (cached?.length && !streaming) {
      loadedForRef.current = sessionId
      setMessages(cached)
      return Promise.resolve()
    }
    return api(`/api/chat/session?session_id=${sessionId}`)
      .then((data) => {
        const msgs = data?.messages?.length > 0
          ? data.messages.map((m) => {
              const srcs = m.sources || []
              return {
                id: m.message_id,
                role: m.role,
                content: m.content,
                sources: srcs.filter((s) => !s.selectable),
                selectableFiles: srcs.filter((s) => s.selectable).map(({ selectable, ...f }) => f),
              }
            })
          : []
        if (!streaming) messagesCacheRef.current[sessionId] = msgs
        loadedForRef.current = sessionId
        setMessages(msgs)
      })
      .catch(() => setMessages([]))
  }

  useEffect(() => {
    if (!sessionId || activeStreamSessionId !== sessionId) return
    streamPollTimer = setInterval(async () => {
      if (activeStreamSessionId !== sessionId) {
        clearInterval(streamPollTimer)
        streamPollTimer = null
        loadMessages(sessionId)
        return
      }
      if (!streamOwnerRef.current) loadMessages(sessionId)
    }, 1500)
    return () => {
      if (streamPollTimer) { clearInterval(streamPollTimer); streamPollTimer = null }
    }
  }, [sessionId])

  function clearAgent() {
    dispatch({ type: 'SET_ACTIVE_AGENT', payload: null })
  }

  const sourcesUsed = messages
    .filter((m) => m.role === 'assistant' && m.sources?.length)
    .flatMap((m) => m.sources)
    .filter((c, i, arr) => arr.findIndex((x) => (x.id || x.file_id) === (c.id || c.file_id)) === i)
    .filter((s) => !s.selectable)

  function appendReply(result) {
    setMessages((prev) => [...prev, {
      id: uuidCounter++,
      role: 'assistant',
      content: result.response || '',
      sources: result.sources || [],
      suggestions: result.suggestions || [],
      selectableFiles: result.selectable_files || [],
    }])
  }

  async function streamChat(content, fileIds) {
    const tempId = uuidCounter++
    streamOwnerRef.current = true
    activeStreamSessionId = sessionId
    setMessages((prev) => [...prev, { id: tempId, role: 'assistant', content: '', sources: [], suggestions: [], selectableFiles: [] }])
    const agentScope = activeAgent ? `${activeAgent.name}: ${activeAgent.scope}` : undefined

    const body = { question: content, session_id: sessionId, department: activeDept, agent_scope: agentScope }
    if (fileIds?.length) body.file_ids = fileIds

    const res = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(body),
      signal: abortRef.current?.signal,
    })

    const isSse = (res.headers.get('content-type') || '').includes('text/event-stream')
    if (!isSse || !res.body) {
      activeStreamSessionId = null
      streamOwnerRef.current = false
      const data = await res.json().catch(() => ({}))
      setMessages((prev) => prev.map((m) => (m.id === tempId
        ? { ...m, content: data.response || data.error || 'Sorry, I encountered an error. Please try again.', selectableFiles: data.selectable_files || [] }
        : m)))
      return
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    const patch = (fn) => setMessages((prev) => prev.map((m) => (m.id === tempId ? fn(m) : m)))
    let finalAnswer = ''

    for (;;) {
      let chunk
      try {
        chunk = await reader.read()
      } catch {
        if (abortRef.current?.signal.aborted) break
        throw err
      }
      const { done, value } = chunk
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
          finalAnswer = d.response ?? ''
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
    activeStreamSessionId = null
    streamOwnerRef.current = false
    if (streamPollTimer) { clearInterval(streamPollTimer); streamPollTimer = null }
    if (finalAnswer && !aiChatMounted) {
      notifyAwayUser(content, finalAnswer)
    }
  }

  function notifyAwayUser(question, answer) {
    const snippet = question.length > 60 ? question.slice(0, 60) + '\u2026' : question
    fetch('/api/notifications/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({
        type: 'ai',
        title: 'AI response ready',
        message: snippet,
        link: '/ai/chat',
      }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.id) {
          dispatch({
            type: 'ADD_NOTIFICATION',
            payload: {
              id: data.id,
              type: 'ai',
              title: 'AI response ready',
              message: snippet,
              link: '/ai/chat',
              unread: true,
              time: 'Just now',
            },
          })
        }
      })
      .catch(() => {})
  }

  async function handleSend(text, fileIds) {
    let content = (text ?? input).trim()
    if (!content) return
    const mentionIds = fileIds ? [...fileIds] : []
    const mentions = [...content.matchAll(/@([\w.\- ]+)/g)].map((m) => m[1].trim()).filter(Boolean)
    if (mentions.length > 0) {
      mentions.forEach((name) => {
        const doc = indexedDocs.find((d) => d.name.toLowerCase() === name.toLowerCase())
        if (doc && !mentionIds.includes(doc.file_id)) mentionIds.push(doc.file_id)
      })
      content = content.replace(/@[\w.\- ]+/g, '').replace(/\s+/g, ' ').trim()
    }
    if (!content) return
    setInput('')
    setMessages((prev) => [...prev, { id: uuidCounter++, role: 'user', content }])
    setIsTyping(true)
    abortRef.current = new AbortController()

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
            ...(mentionIds.length ? { file_ids: mentionIds } : {}),
          }),
        })
        appendReply(result)
      } else {
        await streamChat(content, mentionIds)
      }
      dispatch({
        type: 'ADD_ACTIVITY',
        payload: {
id: uuidCounter++,
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
        id: uuidCounter++ + 1,
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }])
    } finally {
      abortRef.current = null
      setIsTyping(false)
    }
  }

  function stopResponse() {
    abortRef.current?.abort()
    setIsTyping(false)
  }

  function newChat() {
    setMessages([])
    setActiveConv(null)
    api('/api/chat/sessions', { method: 'POST', body: '{}' })
      .then((data) => {
        setSessionId(data.session.session_id)
        loadedForRef.current = data.session.session_id
        setSessions((prev) => [data.session, ...prev])
        toast('Started a new conversation', 'info')
      })
      .catch(() => toast('Could not create session', 'error'))
  }

  const mentionOpen = /(^|\s)@[^\s]*$/.test(input) && !input.endsWith(' ')
  useEffect(() => {
    if (mentionOpen && mentionListRef.current) {
      mentionListRef.current.querySelector('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
    }
  }, [mentionIdx, mentionOpen])
  const mentionQuery = mentionOpen ? input.split(/\s+/).pop().slice(1) : ''
  const mentionFiltered = indexedDocs.filter((d) =>
    d.name.toLowerCase().includes(mentionQuery.toLowerCase())
  )

  function handleInputChange(value) {
    setInput(value)
    if (!/(^|\s)@[^\s]*$/.test(value) || value.endsWith(' ')) {
      setMentionIdx(0)
    }
  }

  function insertMention(doc) {
    const tokens = input.split(/\s+/)
    tokens[tokens.length - 1] = `@${doc.name} `
    setInput(tokens.join(' '))
    inputRef.current?.focus()
  }

  function handleInputKeyDown(e) {
    if (!mentionOpen) return
    if (e.key === 'Escape') {
      setMentionIdx(0)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setMentionIdx((i) => (i + 1) % Math.max(mentionFiltered.length, 1))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      setMentionIdx((i) => (i - 1 + mentionFiltered.length) % Math.max(mentionFiltered.length, 1))
      return
    }
    if (e.key === 'Enter' && mentionFiltered.length > 0) {
      e.preventDefault()
      insertMention(mentionFiltered[Math.min(mentionIdx, mentionFiltered.length - 1)])
    }
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
                      loadMessages(s.session_id)
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
                            loadMessages(data.current_session_id)
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
            {messages.map((msg, mi) => (
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
                      {msg.selectableFiles?.length > 0 && (
                        <div className="pl-1">
                          <ul className="space-y-1.5">
                            {msg.selectableFiles.map((f) => (
                              <li key={f.file_id}>
                                <button
                                  type="button"
                                  disabled={isTyping}
                                  onClick={() => {
                                    const orig = [...messages.slice(0, mi)].reverse().find((m) => m.role === 'user')
                                    handleSend(orig?.content || msg.content, [f.file_id])
                                  }}
                                  className="flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-left text-sm text-slate-700 transition hover:border-navy-400 hover:bg-navy-50 hover:text-navy-800 disabled:opacity-50"
                                >
                                  <FileText className="h-4 w-4 shrink-0 text-navy-500" />
                                  <span className="truncate font-medium">{f.name}</span>
                                </button>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
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
              <div className="relative flex-1">
                {mentionOpen && mentionFiltered.length > 0 && (
                  <div ref={mentionListRef} className="absolute bottom-full left-0 z-20 mb-2 max-h-48 w-full overflow-y-auto rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg">
                    {mentionFiltered.map((d, i) => (
                      <button
                        key={d.file_id}
                        type="button"
                        data-active={i === mentionIdx}
                        onMouseDown={(e) => e.preventDefault()}
                        onClick={() => insertMention(d)}
                        className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm ${
                          i === mentionIdx ? 'bg-navy-50 text-navy-800' : 'text-slate-700'
                        }`}
                      >
                        <FileText className="h-4 w-4 shrink-0 text-navy-500" />
                        <span className="truncate font-medium">{d.name}</span>
                      </button>
                    ))}
                  </div>
                )}
                <input
                  ref={inputRef}
                  type="text"
                  value={input}
                  onChange={(e) => handleInputChange(e.target.value)}
                  onKeyDown={handleInputKeyDown}
                  placeholder="Ask anything about school knowledge..."
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
                />
              </div>
              {isTyping ? (
                <button
                  type="button"
                  onClick={stopResponse}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-600 text-white hover:bg-red-700"
                  aria-label="Stop generating"
                >
                  <Square className="h-4 w-4 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-navy-900 text-white hover:bg-navy-800 disabled:opacity-40"
                >
                  <Send className="h-4 w-4" />
                </button>
              )}
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
                  <p className="truncate rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-xs font-semibold text-slate-800">
                    {s.name || s.source}
                  </p>
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
  return <Markdown text={text} />
}
