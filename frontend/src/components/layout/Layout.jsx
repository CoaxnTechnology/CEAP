import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import CommandPalette from './CommandPalette'
import AICopilot from './AICopilot'
import { useApp } from '../../context/AppContext'

export default function Layout() {
  const { darkMode, dispatch, copilotOpen } = useApp()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [commandOpen, setCommandOpen] = useState(false)

  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setCommandOpen(true)
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'j') {
        e.preventDefault()
        dispatch({ type: 'SET_COPILOT', payload: !copilotOpen })
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [copilotOpen, dispatch])

  return (
    <div className={`min-h-screen ${darkMode ? 'bg-slate-950' : 'bg-[#f6f7fb]'}`}>
      <div className="hidden lg:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed((v) => !v)}
        />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/50" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10 h-full w-[260px]" onClick={() => setMobileOpen(false)}>
            <Sidebar collapsed={false} onToggle={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      <div
        className={`flex min-h-screen flex-col transition-all duration-300 ${
          sidebarCollapsed ? 'lg:ml-[72px]' : 'lg:ml-[260px]'
        }`}
      >
        <Header
          onMenuClick={() => setMobileOpen(true)}
          darkMode={darkMode}
          onToggleDark={() => dispatch({ type: 'SET_DARK_MODE', payload: !darkMode })}
          onOpenCommand={() => setCommandOpen(true)}
          onOpenCopilot={() => dispatch({ type: 'SET_COPILOT', payload: true })}
        />
        <main className="flex-1 overflow-x-hidden p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
      <AICopilot open={copilotOpen} onClose={() => dispatch({ type: 'SET_COPILOT', payload: false })} />
    </div>
  )
}
