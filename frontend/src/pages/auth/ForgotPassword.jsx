import { useState } from 'react'
import { Link } from 'react-router-dom'
import { GraduationCap, ArrowLeft, Mail } from 'lucide-react'
import Button from '../../components/ui/Button'
import { useApp } from '../../context/AppContext'

export default function ForgotPassword() {
  const { toast } = useApp()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      setSent(true)
      toast(`Reset link sent to ${email}`, 'success')
    }, 800)
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
          {!sent ? (
            <>
              <h1 className="text-xl font-bold text-slate-900">Reset password</h1>
              <p className="mt-1 text-sm text-slate-500">
                Enter your work email and we&apos;ll send a reset link (prototype simulation).
              </p>
              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-600">Email</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@school.edu"
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Sending…' : 'Send reset link'}
                </Button>
              </form>
            </>
          ) : (
            <div className="text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success-50 text-success-600">
                <Mail className="h-6 w-6" />
              </div>
              <h1 className="mt-4 text-xl font-bold text-slate-900">Check your inbox</h1>
              <p className="mt-2 text-sm text-slate-500">
                If an account exists for <strong>{email}</strong>, a reset link has been sent.
                (Demo: no real email is sent.)
              </p>
              <Button
                className="mt-6 w-full"
                onClick={() => {
                  setSent(false)
                  setEmail('')
                }}
                variant="secondary"
              >
                Try another email
              </Button>
            </div>
          )}

          <Link
            to="/login"
            className="mt-6 flex items-center justify-center gap-1.5 text-sm font-medium text-navy-700 hover:text-navy-900"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
