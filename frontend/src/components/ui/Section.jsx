import Card from './Card'

export default function Section({ title, subtitle, action, children, padding = true, className = '' }) {
  return (
    <Card className={className} padding={false}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-5 py-3.5">
          <div>
            {title && <h2 className="text-sm font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="text-[11px] text-slate-400">{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      <div className={padding ? 'p-5' : ''}>{children}</div>
    </Card>
  )
}
