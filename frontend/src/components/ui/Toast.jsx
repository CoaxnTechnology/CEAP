import { CheckCircle2, AlertTriangle, Info, X, XCircle } from 'lucide-react'
import { useApp } from '../../context/AppContext'

const icons = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
}

const styles = {
  success: 'border-success-100 bg-white text-success-700',
  error: 'border-danger-100 bg-white text-danger-600',
  warning: 'border-warning-100 bg-white text-warning-600',
  info: 'border-navy-100 bg-white text-navy-800',
}

export default function ToastContainer() {
  const { toasts, dispatch } = useApp()

  if (!toasts.length) return null

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0">
      {toasts.map((t) => {
        const Icon = icons[t.type] || Info
        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-lg animate-in ${styles[t.type] || styles.info}`}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <p className="flex-1 text-sm font-medium text-slate-800">{t.message}</p>
            <button
              type="button"
              onClick={() => dispatch({ type: 'REMOVE_TOAST', payload: t.id })}
              className="rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
