import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  GraduationCap,
  Users,
  UserPlus,
  Wallet,
  Briefcase,
  ShieldCheck,
  Library,
  Sparkles,
  Settings,
  PanelLeftClose,
  PanelLeft,
  CheckSquare,
  CalendarDays,
  GitBranch,
  BarChart3,
  ListTodo,
} from 'lucide-react'
import { useApp } from '../../context/AppContext'
import { workspaces } from '../../data/osData'

const iconMap = {
  LayoutDashboard,
  GraduationCap,
  Users,
  UserPlus,
  Wallet,
  Briefcase,
  ShieldCheck,
  Library,
  Sparkles,
  Settings,
}

const utility = [
  { to: '/tasks', label: 'Tasks', icon: ListTodo },
  { to: '/approvals', label: 'Approvals', icon: CheckSquare },
  { to: '/calendar', label: 'Calendar', icon: CalendarDays },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/workflows', label: 'Workflows', icon: GitBranch },
]

export default function Sidebar({ collapsed, onToggle }) {
  const { school } = useApp()

  return (
    <aside
      className={`fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-white/10 bg-navy-950 text-white transition-all duration-300 ${
        collapsed ? 'w-[72px]' : 'w-[260px]'
      }`}
    >
      <div className="flex h-16 items-center gap-3 border-b border-white/10 px-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-navy-600 to-navy-900 ring-1 ring-white/20">
          <GraduationCap className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-bold tracking-wide">CEAP</div>
            <div className="truncate text-[10px] text-navy-300">AI Operating System</div>
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          className="hidden rounded-lg p-1.5 text-navy-300 hover:bg-white/10 hover:text-white lg:block"
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto px-2 py-4">
        <div>
          {!collapsed && (
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-navy-400">
              Workspaces
            </p>
          )}
          <div className="space-y-0.5">
            {workspaces.map((w) => {
              const Icon = iconMap[w.icon] || LayoutDashboard
              return (
                <NavLink
                  key={w.id}
                  to={w.path}
                  end={w.path === '/'}
                  title={collapsed ? w.label : w.desc}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition ${
                      isActive
                        ? 'bg-white/12 text-white shadow-sm ring-1 ring-white/10'
                        : 'text-navy-100/90 hover:bg-white/8 hover:text-white'
                    }`
                  }
                >
                  <Icon className="h-[18px] w-[18px] shrink-0 opacity-90" />
                  {!collapsed && <span className="truncate">{w.label}</span>}
                </NavLink>
              )
            })}
          </div>
        </div>

        <div>
          {!collapsed && (
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-navy-400">
              Operations
            </p>
          )}
          <div className="space-y-0.5">
            {utility.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                title={collapsed ? label : undefined}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2 text-[13px] font-medium transition ${
                    isActive
                      ? 'bg-white/12 text-white'
                      : 'text-navy-200 hover:bg-white/8 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!collapsed && <span className="truncate">{label}</span>}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {!collapsed && (
        <div className="border-t border-white/10 p-3">
          <div className="rounded-xl bg-white/5 px-3 py-2.5 ring-1 ring-white/10">
            <p className="truncate text-[11px] font-medium text-navy-100">
              {school?.name || 'Your School'}
            </p>
            <p className="text-[10px] text-navy-400">CoAxn · Education Edition</p>
          </div>
        </div>
      )}
    </aside>
  )
}
