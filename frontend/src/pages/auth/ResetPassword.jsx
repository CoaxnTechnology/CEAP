import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { GraduationCap, ArrowLeft } from 'lucide-react'
import Button from '../../components/ui/Button'
import { useApp } from '../../context/AppContext'

export default function ResetPassword() {
  const { toast } = useApp()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (pw.length < 4) { setError('Password must be at least 4 characters.'); return }
    if (pw !== confirm) { setError('Passwords do not match.'); return }
    if (!token) { setError('Invalid or missing token.'); return }
    setLoading(true)
    try {
      const res = await fetch('/api/auth/reset-password', { method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include', body: JSON.stringify({ token, new_password: pw }) })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Failed')
      toast('Password reset successful. Please sign in.', 'success')
      navigate('/login', { replace: true })
    } catch (err) {
      setError(err.message || 'Could not reset password')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
        <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm text-center">
          <p className="text-sm text-danger-600">Invalid reset link.</p>
          <Link to="/forgot-password" className="mt-4 inline-block text-sm font-medium text-navy-700">Request a new link</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-white">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold text-slate-900">CEAP</span>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h1 className="text-xl font-bold text-slate-900">Set new password</h1>
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">New password</label>
              <input type="password" required value={pw} onChange={(e) => setPw(e.target.value)} placeholder="At least 4 characters" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100" />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">Confirm password</label>
              <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat password" className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100" />
            </div>
            {error && <p className="text-sm text-danger-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>{loading ? 'Saving…' : 'Reset password'}</Button>
          </form>
          <Link to="/login" className="mt-6 flex items-center justify-center gap-1.5 text-sm font-medium text-navy-700 hover:text-navy-900">
            <ArrowLeft className="h-4 w-4" />Back to sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
