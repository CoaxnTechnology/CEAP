import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, LockKeyhole, ArrowRight } from 'lucide-react'
import { useApp } from '../../context/AppContext'
import Button from '../../components/ui/Button'

export default function SetPassword() {
  const { changePassword, logout } = useApp()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (next.length < 4) { setError('Password must be at least 4 characters.'); return }
    if (next !== confirm) { setError('Passwords do not match.'); return }
    if (next === current) { setError('New password must differ from current.'); return }
    setLoading(true)
    const res = await changePassword(current, next)
    setLoading(false)
    if (!res.ok) { setError(res.error || 'Failed to change password'); return }
    navigate('/', { replace: true })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-white">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-bold text-slate-900">CEAP</p>
            <p className="text-[11px] text-slate-500">Education Edition</p>
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-50 text-navy-700">
              <LockKeyhole className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-900">Set your password</h2>
              <p className="text-xs text-slate-500">You're using a temporary password. Create your own to continue.</p>
            </div>
          </div>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">Temporary password</label>
              <input type="password" required value={current} onChange={(e) => setCurrent(e.target.value)}
                placeholder="Enter the password you signed in with"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">New password</label>
              <input type="password" required value={next} onChange={(e) => setNext(e.target.value)}
                placeholder="At least 4 characters"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">Confirm new password</label>
              <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)}
                placeholder="Repeat new password"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100" />
            </div>
            {error && (
              <div className="rounded-lg border border-danger-100 bg-danger-50 px-3 py-2 text-sm text-danger-600">{error}</div>
            )}
            <Button type="submit" className="w-full" disabled={loading} size="lg">
              {loading ? 'Saving…' : 'Set password & continue'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>
          <button type="button" onClick={() => logout()} className="mt-4 w-full text-center text-xs font-medium text-slate-400 hover:text-slate-600">
            Sign out
          </button>
        </div>
      </div>
    </div>
  )
}