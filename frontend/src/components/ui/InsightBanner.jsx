import { Sparkles } from 'lucide-react'

export default function InsightBanner({ title = 'AI Insights', items = [], className = '' }) {
  return (
    <div
      className={`rounded-2xl border border-violet-100 bg-gradient-to-br from-violet-50 via-white to-navy-50 p-5 ${className}`}
    >
      <div className="mb-3 flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-600 text-white shadow-sm">
          <Sparkles className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">{title}</p>
          <p className="text-[11px] text-slate-400">Contextual recommendations from CEAP</p>
        </div>
      </div>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-700">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500" />
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
