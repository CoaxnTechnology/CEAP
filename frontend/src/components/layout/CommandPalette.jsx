import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, CornerDownLeft } from 'lucide-react'
import { commandItems } from '../../data/osData'

export default function CommandPalette({ open, onClose }) {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [active, setActive] = useState(0)

  const results = useMemo(() => {
    const query = q.trim().toLowerCase()
    if (!query) return commandItems
    return commandItems.filter(
      (i) =>
        i.label.toLowerCase().includes(query) ||
        i.keywords.includes(query) ||
        i.group.toLowerCase().includes(query)
    )
  }, [q])

  useEffect(() => {
    if (!open) {
      setQ('')
      setActive(0)
    }
  }, [open])

  useEffect(() => {
    setActive(0)
  }, [q])

  useEffect(() => {
    const el = document.querySelector('[data-cmd-active="true"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [active])

  useEffect(() => {
    if (!open) return
    function onKey(e) {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActive((a) => Math.min(a + 1, results.length - 1))
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActive((a) => Math.max(a - 1, 0))
      }
      if (e.key === 'Enter' && results[active]) {
        navigate(results[active].path)
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, results, active, navigate, onClose])

  if (!open) return null

  const groups = [...new Set(results.map((r) => r.group))]

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center bg-slate-900/40 px-4 pt-[12vh] backdrop-blur-sm">
      <div
        className="absolute inset-0"
        onClick={onClose}
        aria-hidden
      />
      <div className="relative z-10 w-full max-w-xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
        <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search workspaces, actions, students…"
            className="flex-1 border-0 bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
          <kbd className="rounded border border-slate-200 px-1.5 py-0.5 text-[10px] text-slate-400">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto py-2">
          {results.length === 0 && (
            <p className="px-4 py-8 text-center text-sm text-slate-400">No matches</p>
          )}
          {groups.map((g) => (
            <div key={g}>
              <p className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                {g}
              </p>
              {results
                .filter((r) => r.group === g)
                .map((item) => {
                  const idx = results.indexOf(item)
                  return (
                    <button
                      key={item.id}
                      type="button"
                      data-cmd-active={idx === active ? 'true' : 'false'}
                      onMouseEnter={() => setActive(idx)}
                      onClick={() => {
                        navigate(item.path)
                        onClose()
                      }}
                      className={`flex w-full items-center justify-between px-4 py-2.5 text-left text-sm ${
                        idx === active ? 'bg-navy-50 text-navy-900' : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-medium">{item.label}</span>
                      {idx === active && <CornerDownLeft className="h-3.5 w-3.5 text-navy-400" />}
                    </button>
                  )
                })}
            </div>
          ))}
        </div>
        <div className="border-t border-slate-100 px-4 py-2 text-[10px] text-slate-400">
          ↑↓ navigate · ↵ open · ⌘K anytime
        </div>
      </div>
    </div>
  )
}
