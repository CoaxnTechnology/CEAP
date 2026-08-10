import { Navigate, useLocation } from 'react-router-dom'
import { useApp } from '../../context/AppContext'

export default function ProtectedRoute({ children, requireOnboarding = true }) {
  const { isAuthenticated, onboardingComplete } = useApp()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (requireOnboarding && !onboardingComplete && !location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/onboarding" replace />
  }

  if (onboardingComplete && location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/" replace />
  }

  return children
}
