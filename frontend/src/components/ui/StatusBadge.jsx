const styles = {
  Current: 'bg-success-50 text-success-700 border-success-100',
  Available: 'bg-success-50 text-success-700 border-success-100',
  Ready: 'bg-success-50 text-success-700 border-success-100',
  Connected: 'bg-success-50 text-success-700 border-success-100',
  Completed: 'bg-success-50 text-success-700 border-success-100',
  Expiring: 'bg-warning-50 text-warning-600 border-warning-100',
  Upcoming: 'bg-blue-50 text-blue-700 border-blue-100',
  'In Progress': 'bg-blue-50 text-blue-700 border-blue-100',
  Draft: 'bg-slate-100 text-slate-600 border-slate-200',
  Missing: 'bg-danger-50 text-danger-600 border-danger-100',
  Outdated: 'bg-orange-50 text-orange-700 border-orange-100',
  'Not Connected': 'bg-slate-100 text-slate-500 border-slate-200',
  critical: 'bg-danger-50 text-danger-600 border-danger-100',
  high: 'bg-orange-50 text-orange-700 border-orange-100',
  medium: 'bg-warning-50 text-warning-600 border-warning-100',
  low: 'bg-slate-100 text-slate-600 border-slate-200',
  Active: 'bg-success-50 text-success-700 border-success-100',
  Invited: 'bg-blue-50 text-blue-700 border-blue-100',
  Suspended: 'bg-danger-50 text-danger-600 border-danger-100',
}

export default function StatusBadge({ status, className = '' }) {
  const style = styles[status] || 'bg-slate-100 text-slate-600 border-slate-200'
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${style} ${className}`}
    >
      {status}
    </span>
  )
}
