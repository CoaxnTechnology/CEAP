import { useState } from 'react'
import { Link, useNavigate, useLocation, Navigate } from 'react-router-dom'
import { GraduationCap, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { useApp } from '../../context/AppContext'
import Button from '../../components/ui/Button'

export default function Login() {
  const { login, isAuthenticated, onboardingComplete } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('login')

  if (isAuthenticated) {
    return <Navigate to={onboardingComplete ? '/' : '/onboarding'} replace />
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (mode === 'register') {
      setLoading(true)
      try {
        const res = await fetch('/api/onboarding/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name.trim(), email: email.trim(), password }),
        })
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          setError(err.error || 'Signup failed')
          setLoading(false)
          return
        }
        const result = await login(email, password)
        setLoading(false)
        if (result.ok) {
          navigate('/onboarding', { replace: true })
        } else {
          setError(result.error || 'Login failed after signup')
        }
      } catch {
        setLoading(false)
        setError('Network error. Is the server running?')
      }
      return
    }
    setLoading(true)
    setTimeout(async () => {
      const result = await login(email, password)
      setLoading(false)
      if (!result.ok) {
        setError(result.error)
        return
      }
      const from = location.state?.from?.pathname
      if (result.mustChangePassword) {
        navigate('/set-password', { replace: true })
      } else if (result.needsOnboarding) {
        navigate('/onboarding', { replace: true })
      } else {
        navigate(from && from !== '/login' ? from : '/', { replace: true })
      }
    }, 600)
  }

  function startNewSchool() {
    setMode('register')
    setEmail('')
    setPassword('')
    setName('')
    setError('')
  }

  return (
    <div className="flex min-h-screen">
      {/* Brand panel */}
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-navy-900 p-10 text-white lg:flex">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_rgba(255,255,255,0.08),_transparent_50%)]" />
        <div className="relative flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/20">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-bold tracking-wide">CEAP</p>
            <p className="text-[11px] text-navy-200">CoAxn Enterprise AI Platform</p>
          </div>
        </div>
        <div className="relative max-w-md">
          <p className="text-xs font-semibold uppercase tracking-widest text-navy-300">
            Education Edition
          </p>
          <h1 className="mt-3 text-4xl font-bold leading-tight">
            The AI Operating System for Schools
          </h1>
          <p className="mt-4 text-base leading-relaxed text-navy-100">
            The central intelligence layer for your school — Student 360, Finance Intelligence,
            multi-agent AI, compliance readiness, and institutional memory. Not an ERP. An OS.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-navy-100">
            {[
              'Executive morning briefing & approvals',
              'Student 360 with AI risk & timelines',
              'Finance, Admissions & HR intelligence',
              'Multi-agent AI with human publish gates',
            ].map((item) => (
              <li key={item} className="flex items-center gap-2">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-success-500/20 text-success-500 text-xs">
                  ✓
                </span>
                {item}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-navy-300">© 2025 CoAxn · Prototype UI</p>
      </div>

      {/* Form panel */}
      <div className="flex w-full flex-col justify-center px-6 py-12 lg:w-1/2 lg:px-16">
        <div className="mx-auto w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-navy-900 text-white">
              <GraduationCap className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-900">CEAP</p>
              <p className="text-[11px] text-slate-500">Education Edition</p>
            </div>
          </div>

          <h2 className="text-2xl font-bold text-slate-900">
            {mode === 'login' ? 'Sign in to your school' : 'Create your CEAP account'}
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            {mode === 'login'
              ? 'Access knowledge, compliance, and AI tools for your institution.'
              : 'Start school onboarding after creating your admin account.'}
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            {mode === 'register' && (
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-600">Full name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Dr. Ananya Gupta"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
                />
              </div>
            )}
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-600">Work email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@school.edu"
                className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
              />
            </div>
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label className="text-xs font-medium text-slate-600">Password</label>
                {mode === 'login' && (
                  <Link
                    to="/forgot-password"
                    className="text-xs font-medium text-navy-600 hover:text-navy-800"
                  >
                    Forgot password?
                  </Link>
                )}
              </div>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 pr-10 text-sm outline-none focus:border-navy-400 focus:bg-white focus:ring-2 focus:ring-navy-100"
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-1 text-slate-400 hover:text-slate-600"
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg border border-danger-100 bg-danger-50 px-3 py-2 text-sm text-danger-600">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading} size="lg">
              {loading ? 'Signing in…' : mode === 'login' ? 'Sign in' : 'Create account & continue'}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </Button>
          </form>

          <div className="mt-6 space-y-3">
            {mode === 'login' ? (
              <p className="text-center text-sm text-slate-500">
                New school?{' '}
                <button
                  type="button"
                  onClick={startNewSchool}
                  className="font-semibold text-navy-700 hover:underline"
                >
                  Start onboarding
                </button>
              </p>
            ) : (
              <p className="text-center text-sm text-slate-500">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setMode('login')
                    setError('')
                  }}
                  className="font-semibold text-navy-700 hover:underline"
                >
                  Sign in
                </button>
              </p>
            )}
          </div>


        </div>
      </div>
    </div>
  )
}
