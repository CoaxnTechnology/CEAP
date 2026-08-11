import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { AppProvider } from './context/AppContext'
import ProtectedRoute from './components/auth/ProtectedRoute'
import ToastContainer from './components/ui/Toast'
import Layout from './components/layout/Layout'

import Login from './pages/auth/Login'
import ForgotPassword from './pages/auth/ForgotPassword'
import SetPassword from './pages/auth/SetPassword'
import Onboarding from './pages/onboarding/Onboarding'
import Legal from './pages/Legal'

import Executive from './pages/Executive'
import Academic from './pages/Academic'
import Students from './pages/students/Students'
import Student360 from './pages/students/Student360'
import Admissions from './pages/Admissions'
import Finance from './pages/Finance'
import HR from './pages/HR'
import Compliance from './pages/Compliance'
import KnowledgeHub from './pages/knowledge/KnowledgeHub'
import SchoolMemory from './pages/knowledge/SchoolMemory'
import AIWorkspace from './pages/ai/AIWorkspace'
import AIChat from './pages/AIChat'
import Generate from './pages/Generate'
import Admin from './pages/Admin'
import UsersAdmin from './pages/UsersAdmin'
import RolesAdmin from './pages/RolesAdmin'
import Workflows from './pages/Workflows'
import Analytics from './pages/Analytics'
import Tasks from './pages/Tasks'
import Approvals from './pages/Approvals'
import CalendarPage from './pages/CalendarPage'
import SearchPage from './pages/SearchPage'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import ActivityPage from './pages/ActivityPage'
import Meetings from './pages/Meetings'
import DocumentDetail from './pages/DocumentDetail'
import KnowledgeLibrary from './pages/KnowledgeLibrary'

function OAuthWatcher() {
  const navigate = useNavigate()
  const location = useLocation()
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (params.get('od_connected') === '1' && sessionStorage.getItem('onboarding_step')) {
      navigate('/onboarding?od_connected=1', { replace: true })
    }
  }, [location.search])
  return null
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <OAuthWatcher />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/set-password" element={<SetPassword />} />
          <Route path="/privacy" element={<Legal type="privacy" />} />
          <Route path="/terms" element={<Legal type="terms" />} />

          <Route
            path="/onboarding"
            element={
              <ProtectedRoute requireOnboarding={false}>
                <Onboarding />
              </ProtectedRoute>
            }
          />

          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Executive />} />
            <Route path="academic" element={<Academic />} />
            <Route path="students" element={<Students />} />
            <Route path="students/:id" element={<Student360 />} />
            <Route path="admissions" element={<Admissions />} />
            <Route path="finance" element={<Finance />} />
            <Route path="hr" element={<HR />} />
            <Route path="compliance" element={<Compliance />} />
            <Route path="knowledge" element={<KnowledgeHub />} />
            <Route path="knowledge/memory" element={<SchoolMemory />} />
            <Route path="library" element={<KnowledgeLibrary />} />
            <Route path="library/:id" element={<DocumentDetail />} />
            <Route path="document/:id" element={<DocumentDetail />} />
            <Route path="ai" element={<AIWorkspace />} />
            <Route path="ai/chat" element={<AIChat />} />
            <Route path="ai/studio" element={<Generate />} />
            <Route path="chat" element={<Navigate to="/ai/chat" replace />} />
            <Route path="generate" element={<Navigate to="/ai/studio" replace />} />
            <Route path="admin" element={<Admin />} />
            <Route path="admin/users" element={<UsersAdmin />} />
            <Route path="admin/roles" element={<RolesAdmin />} />

            <Route path="workflows" element={<Workflows />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="tasks" element={<Tasks />} />
            <Route path="approvals" element={<Approvals />} />
            <Route path="calendar" element={<CalendarPage />} />
            <Route path="meetings" element={<Meetings />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="activity" element={<ActivityPage />} />
            <Route path="profile" element={<Profile />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <ToastContainer />
      </BrowserRouter>
    </AppProvider>
  )
}
