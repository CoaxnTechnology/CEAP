import { createContext, useContext, useReducer, useEffect, useCallback } from 'react'
import {
  notifications as seedNotifications,
  complianceEvidence as seedEvidence,
  meetings as seedMeetings,
  knowledgeGaps as seedGaps,
  recentActivity as seedActivity,
} from '../data/mockData'

const STORAGE_KEY = 'ceap_session_v1'

const defaultSchool = {
  name: 'Greenwood International School',
  board: 'CBSE',
  city: 'Bengaluru',
  state: 'Karnataka',
  academicYear: '2025-26',
  studentCount: 1200,
  staffCount: 85,
  address: '12 Education Avenue, Whitefield',
  phone: '+91 80 4000 1200',
  website: 'www.greenwood.edu',
}

const seedUsers = [
  { id: 1, name: 'Priya Sharma', email: 'priya.sharma@greenwood.edu', role: 'Principal', status: 'Active', department: 'Admin', lastActive: 'Just now' },
  { id: 2, name: 'Rahul Mehta', email: 'rahul.mehta@greenwood.edu', role: 'HOD', status: 'Active', department: 'HR', lastActive: '28 min ago' },
  { id: 3, name: 'Meera Nair', email: 'meera.nair@greenwood.edu', role: 'HOD', status: 'Active', department: 'Academic', lastActive: '1 hr ago' },
  { id: 4, name: 'Sneha Kapoor', email: 'sneha.kapoor@greenwood.edu', role: 'Admin Staff', status: 'Active', department: 'Finance', lastActive: '2 hrs ago' },
  { id: 5, name: 'Vikram Singh', email: 'vikram.singh@greenwood.edu', role: 'Admin Staff', status: 'Active', department: 'Admin', lastActive: '3 hrs ago' },
  { id: 6, name: 'Anita Desai', email: 'anita.desai@greenwood.edu', role: 'Teacher', status: 'Active', department: 'Admin', lastActive: 'Yesterday' },
  { id: 7, name: 'Amit Joshi', email: 'amit.joshi@greenwood.edu', role: 'Teacher', status: 'Invited', department: 'Transport', lastActive: '—' },
]

function loadSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

async function backendLogin(email, password) {
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ email: email.toLowerCase().trim(), password }),
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

async function backendChangePassword(current, next) {
  try {
    const res = await fetch('/api/me/password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ current_password: current, new_password: next }),
    })
    if (!res.ok) {
      const e = await res.json().catch(() => ({}))
      return { ok: false, error: e.error || 'Password change failed' }
    }
    return { ok: true }
  } catch {
    return { ok: false, error: 'Network error. Is the server running?' }
  }
}

async function backendOnboardingStatus() {
  try {
    const res = await fetch('/api/onboarding/status', { credentials: 'include' })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

const initialState = {
  // Auth
  isAuthenticated: false,
  user: null,
  // Onboarding
  onboardingComplete: false,
  school: null,
  // Domain data (mutable for prototype)
  notifications: seedNotifications,
  evidence: seedEvidence,
  meetings: seedMeetings,
  gaps: seedGaps,
  activity: seedActivity,
  users: seedUsers,
  conversations: [],
  publishedDocs: [],
  evidencePacks: [],
  activeAgent: null,
  copilotOpen: false,
  // UI
  darkMode: false,
  toasts: [],
  // Preferences
  preferences: {
    emailAlerts: true,
    expiringCertReminders: true,
    weeklyDigest: false,
    language: 'English',
  },
}

function hydrate(state, saved) {
  if (!saved) return state
  return {
    ...state,
    isAuthenticated: !!saved.isAuthenticated,
    user: saved.user || null,
    onboardingComplete: !!saved.onboardingComplete,
    school: saved.school || null,
    darkMode: !!saved.darkMode,
    users: saved.users || state.users,
    meetings: saved.meetings || state.meetings,
    evidence: saved.evidence || state.evidence,
    notifications: saved.notifications || state.notifications,
    gaps: saved.gaps || state.gaps,
    activity: saved.activity || state.activity,
    publishedDocs: saved.publishedDocs || [],
    evidencePacks: saved.evidencePacks || [],
    preferences: { ...state.preferences, ...(saved.preferences || {}) },
  }
}

function reducer(state, action) {
  switch (action.type) {
    case 'HYDRATE':
      return hydrate(state, action.payload)

    case 'LOGIN':
      return {
        ...state,
        isAuthenticated: true,
        user: action.payload.user,
        onboardingComplete: action.payload.onboardingComplete,
        school: action.payload.school,
      }

    case 'LOGOUT':
      return {
        ...initialState,
        darkMode: state.darkMode,
      }

    case 'COMPLETE_ONBOARDING':
      return {
        ...state,
        onboardingComplete: true,
        school: action.payload.school,
        user: action.payload.user || state.user,
        activity: [
          {
            id: Date.now(),
            user: action.payload.user?.name || 'System',
            action: 'Completed',
            target: 'School onboarding',
            time: 'Just now',
            type: 'approve',
          },
          ...state.activity,
        ],
      }

    case 'UPDATE_USER':
      return { ...state, user: { ...state.user, ...action.payload } }

    case 'UPDATE_SCHOOL':
      return { ...state, school: { ...state.school, ...action.payload } }

    case 'UPDATE_PREFERENCES':
      return { ...state, preferences: { ...state.preferences, ...action.payload } }

    case 'SET_DARK_MODE':
      return { ...state, darkMode: action.payload }

    case 'ADD_TOAST':
      return { ...state, toasts: [...state.toasts, action.payload] }

    case 'REMOVE_TOAST':
      return { ...state, toasts: state.toasts.filter((t) => t.id !== action.payload) }

    case 'MARK_NOTIF_READ':
      return {
        ...state,
        notifications: state.notifications.map((n) =>
          n.id === action.payload ? { ...n, unread: false } : n
        ),
      }

    case 'MARK_ALL_NOTIFS_READ':
      return {
        ...state,
        notifications: state.notifications.map((n) => ({ ...n, unread: false })),
      }

    case 'CLEAR_NOTIFICATIONS':
      return { ...state, notifications: [] }

    case 'SET_NOTIFICATIONS':
      return { ...state, notifications: action.payload }

    case 'ADD_NOTIFICATION':
      return {
        ...state,
        notifications: [action.payload, ...state.notifications],
      }

    case 'ADD_MEETING':
      return {
        ...state,
        meetings: [action.payload, ...state.meetings],
        activity: [
          {
            id: Date.now(),
            user: state.user?.name || 'Admin',
            action: 'Scheduled',
            target: action.payload.title,
            time: 'Just now',
            type: 'update',
          },
          ...state.activity,
        ],
      }

    case 'UPDATE_MEETING':
      return {
        ...state,
        meetings: state.meetings.map((m) =>
          m.id === action.payload.id ? { ...m, ...action.payload } : m
        ),
      }

    case 'CANCEL_MEETING':
      return {
        ...state,
        meetings: state.meetings.filter((m) => m.id !== action.payload),
      }

    case 'PUBLISH_DOCUMENT': {
      const doc = action.payload
      return {
        ...state,
        publishedDocs: [doc, ...state.publishedDocs],
        activity: [
          {
            id: Date.now(),
            user: state.user?.name || 'User',
            action: 'Approved',
            target: doc.title,
            time: 'Just now',
            type: 'approve',
          },
          ...state.activity,
        ],
        notifications: [
          {
            id: Date.now(),
            title: `Published: ${doc.title}`,
            time: 'Just now',
            unread: true,
            type: 'success',
          },
          ...state.notifications,
        ],
      }
    }

    case 'UPDATE_EVIDENCE':
      return {
        ...state,
        evidence: state.evidence.map((e) =>
          e.id === action.payload.id ? { ...e, ...action.payload } : e
        ),
      }

    case 'ADD_EVIDENCE_PACK':
      return {
        ...state,
        evidencePacks: [action.payload, ...state.evidencePacks],
        activity: [
          {
            id: Date.now(),
            user: state.user?.name || 'User',
            action: 'Generated',
            target: action.payload.name,
            time: 'Just now',
            type: 'generate',
          },
          ...state.activity,
        ],
        notifications: [
          {
            id: Date.now(),
            title: 'Evidence pack ready for download',
            time: 'Just now',
            unread: true,
            type: 'success',
          },
          ...state.notifications,
        ],
      }

    case 'RESOLVE_GAP':
      return {
        ...state,
        gaps: state.gaps.filter((g) => g.id !== action.payload),
        activity: [
          {
            id: Date.now(),
            user: state.user?.name || 'User',
            action: 'Resolved',
            target: 'Knowledge gap',
            time: 'Just now',
            type: 'approve',
          },
          ...state.activity,
        ],
      }

    case 'ADD_ACTIVITY':
      return {
        ...state,
        activity: [action.payload, ...state.activity],
      }

    case 'ADD_CONVERSATION':
      return {
        ...state,
        conversations: [action.payload, ...state.conversations],
      }

    case 'SET_ACTIVE_AGENT':
      return { ...state, activeAgent: action.payload }

    case 'SET_COPILOT':
      return { ...state, copilotOpen: action.payload }

    case 'RESET_DEMO':
      localStorage.removeItem(STORAGE_KEY)
      return { ...initialState }

    default:
      return state
  }
}

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState, (base) =>
    hydrate(base, loadSession())
  )

  // Persist key session fields — dark mode always persisted
  useEffect(() => {
    if (!state.isAuthenticated) {
      try {
        const raw = localStorage.getItem(STORAGE_KEY)
        const prev = raw ? JSON.parse(raw) : {}
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...prev, darkMode: state.darkMode }))
      } catch {}
      return
    }
    const toSave = {
      isAuthenticated: state.isAuthenticated,
      user: state.user,
      onboardingComplete: state.onboardingComplete,
      school: state.school,
      darkMode: state.darkMode,
      users: state.users,
      meetings: state.meetings,
      evidence: state.evidence,
      notifications: state.notifications,
      gaps: state.gaps,
      activity: state.activity,
      publishedDocs: state.publishedDocs,
      evidencePacks: state.evidencePacks,
      preferences: state.preferences,
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave))
    } catch {
      /* ignore quota */
    }
  }, [
    state.isAuthenticated,
    state.user,
    state.onboardingComplete,
    state.school,
    state.darkMode,
    state.users,
    state.meetings,
    state.evidence,
    state.notifications,
    state.gaps,
    state.activity,
    state.publishedDocs,
    state.evidencePacks,
    state.preferences,
  ])

  useEffect(() => {
    document.documentElement.classList.toggle('dark', state.darkMode)
  }, [state.darkMode])

  useEffect(() => {
    if (!state.isAuthenticated) return
    let cancelled = false
    fetch('/api/notifications')
      .then((res) => {
        // Session expired or server restarted — force logout instead of showing a dead app
        if (res.status === 401) {
          dispatch({ type: 'LOGOUT' })
          localStorage.removeItem(STORAGE_KEY)
          return null
        }
        return res.ok ? res.json() : null
      })
      .then((data) => {
        if (data && !cancelled) {
          dispatch({ type: 'SET_NOTIFICATIONS', payload: data.notifications || [] })
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [state.isAuthenticated, state.user])

  const toast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random()
    dispatch({ type: 'ADD_TOAST', payload: { id, message, type } })
    setTimeout(() => dispatch({ type: 'REMOVE_TOAST', payload: id }), 3500)
  }, [])

  const login = useCallback(
    async (email, password) => {
      if (!email?.trim() || !password?.trim()) {
        return { ok: false, error: 'Email and password are required.' }
      }
      if (password.length < 4) {
        return { ok: false, error: 'Password must be at least 4 characters.' }
      }

      const backendUser = await backendLogin(email, password)
      if (!backendUser) {
        return { ok: false, error: 'Invalid credentials. Try again.' }
      }

      let user = null
      let onboardingComplete = false
      let school = null

      const status = await backendOnboardingStatus()
      if (status && status.authenticated) {
        onboardingComplete = status.onboarding_complete
        school = status.school
      } else {
        onboardingComplete = false
        school = null
      }
      const fullName = status?.user?.full_name || backendUser.username || email.split('@')[0]
      user = {
        name: fullName,
        role: backendUser.role || 'user',
        email,
        avatar: fullName
          .split(' ')
          .map((w) => w[0])
          .join('')
          .slice(0, 2)
          .toUpperCase(),
        school: school?.name || 'My School',
      }

      dispatch({
        type: 'LOGIN',
        payload: { user, onboardingComplete, school },
      })

      toast(`Signed in as ${user.name}`, 'success')
      return {
        ok: true,
        needsOnboarding: !onboardingComplete,
        mustChangePassword: Boolean(backendUser.must_change_password),
      }
    },
    [toast]
  )

  const logout = useCallback(() => {
    dispatch({ type: 'LOGOUT' })
    localStorage.removeItem(STORAGE_KEY)
    toast('Signed out successfully', 'info')
  }, [toast])

  const changePassword = useCallback(
    async (current, next) => {
      const res = await backendChangePassword(current, next)
      if (res.ok) toast('Password updated', 'success')
      return res
    },
    [toast]
  )

  const completeOnboarding = useCallback(
    (payload) => {
      dispatch({ type: 'COMPLETE_ONBOARDING', payload })
      toast('School onboarding complete! Welcome to CEAP.', 'success')
    },
    [toast]
  )

  const value = {
    ...state,
    dispatch,
    toast,
    login,
    logout,
    changePassword,
    completeOnboarding,
    defaultSchool,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
