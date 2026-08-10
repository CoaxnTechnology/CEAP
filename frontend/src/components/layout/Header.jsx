import { useState, useRef, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Search,
  Bell,
  Menu,
  Moon,
  Sun,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  Info,
  User,
  Settings,
  LogOut,
  Sparkles,
  Command,
} from 'lucide-react'
import { useApp } from '../../context/AppContext'

export default function Header({
  onMenuClick,
  darkMode,
  onToggleDark,
  onOpenCommand,
  onOpenCopilot,
}) {
  const navigate = useNavigate()
  const { user, school, notifications, dispatch, logout, toast } = useApp()
  const [query, setQuery] = useState('')
  const [showNotifs, setShowNotifs] = useState(false)
  const [showUser, setShowUser] = useState(false)
  const notifRef = useRef(null)
  const userRef = useRef(null)
  const unread = notifications.filter((n) => n.unread).length

  useEffect(() => {
    function handleClick(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) setShowNotifs(false)
      if (userRef.current && !userRef.current.contains(e.target)) setShowUser(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  function handleSearch(e) {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
    } else {
      onOpenCommand?.()
    }
  }

  const iconFor = (type) => {
    if (type === 'warning' || type === 'alert') return AlertTriangle
    if (type === 'success') return CheckCircle2
    return Info
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl lg:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-xl p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
      >
        <Menu className="h-5 w-5" />
      </button>

      <form onSubmit={handleSearch} className="relative max-w-xl flex-1">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <input
          id="global-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Universal search — students, knowledge, decisions…"
          className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2.5 pl-10 pr-24 text-sm outline-none transition focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
        />
        <button
          type="button"
          onClick={onOpenCommand}
          className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-medium text-slate-400 hover:text-slate-600"
        >
          <Command className="h-3 w-3" /> K
        </button>
      </form>

      <div className="ml-auto flex items-center gap-1 sm:gap-1.5">
        <button
          type="button"
          onClick={onOpenCopilot}
          className="inline-flex items-center gap-1.5 rounded-xl bg-navy-900 px-3 py-2 text-xs font-semibold text-white shadow-sm hover:bg-navy-800"
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">AI</span>
        </button>

        <button
          type="button"
          onClick={onToggleDark}
          className="rounded-xl p-2 text-slate-500 hover:bg-slate-100"
        >
          {darkMode ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </button>

        <div className="relative" ref={notifRef}>
          <button
            type="button"
            onClick={() => setShowNotifs((v) => !v)}
            className="relative rounded-xl p-2 text-slate-500 hover:bg-slate-100"
          >
            <Bell className="h-[18px] w-[18px]" />
            {unread > 0 && (
              <span className="absolute right-1.5 top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-danger-500 text-[9px] font-bold text-white">
                {unread}
              </span>
            )}
          </button>
          {showNotifs && (
            <div className="absolute right-0 mt-2 w-80 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
              <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <span className="text-sm font-semibold">Notifications</span>
                <button
                  type="button"
                  className="text-xs font-medium text-navy-600"
                  onClick={() => {
                    dispatch({ type: 'MARK_ALL_NOTIFS_READ' })
                    toast('All marked read', 'success')
                  }}
                >
                  Mark all read
                </button>
              </div>
              <ul className="max-h-72 overflow-y-auto">
                {notifications.map((n) => {
                  const Icon = iconFor(n.type)
                  return (
                    <li key={n.id}>
                      <button
                        type="button"
                        onClick={() => {
                          dispatch({ type: 'MARK_NOTIF_READ', payload: n.id })
                          setShowNotifs(false)
                          navigate('/tasks')
                        }}
                        className={`flex w-full gap-3 px-4 py-3 text-left hover:bg-slate-50 ${
                          n.unread ? 'bg-navy-50/40' : ''
                        }`}
                      >
                        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-navy-500" />
                        <div>
                          <p className="text-sm text-slate-700">{n.title}</p>
                          <p className="text-xs text-slate-400">{n.time}</p>
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </div>

        <div className="relative" ref={userRef}>
          <button
            type="button"
            onClick={() => setShowUser((v) => !v)}
            className="flex items-center gap-2 rounded-xl py-1 pl-1 pr-2 hover:bg-slate-100"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-navy-700 to-navy-950 text-xs font-semibold text-white">
              {user?.avatar || 'U'}
            </div>
            <div className="hidden text-left sm:block">
              <p className="text-sm font-medium leading-tight text-slate-800">{user?.name}</p>
              <p className="text-[11px] leading-tight text-slate-400">{user?.role}</p>
            </div>
            <ChevronDown className="hidden h-3.5 w-3.5 text-slate-400 sm:block" />
          </button>
          {showUser && (
            <div className="absolute right-0 mt-2 w-60 overflow-hidden rounded-2xl border border-slate-200 bg-white py-1 shadow-xl">
              <div className="border-b border-slate-100 px-4 py-3">
                <p className="text-sm font-semibold">{user?.name}</p>
                <p className="text-xs text-slate-500">{user?.email}</p>
                <p className="mt-1 text-[11px] text-navy-600">{school?.name || user?.school}</p>
              </div>
              <Link to="/profile" onClick={() => setShowUser(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                <User className="h-4 w-4" /> Profile
              </Link>
              <Link to="/settings" onClick={() => setShowUser(false)} className="flex items-center gap-2 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50">
                <Settings className="h-4 w-4" /> Preferences
              </Link>
              <button
                type="button"
                onClick={() => {
                  setShowUser(false)
                  logout()
                  navigate('/login')
                }}
                className="flex w-full items-center gap-2 px-4 py-2 text-sm text-danger-600 hover:bg-danger-50"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
