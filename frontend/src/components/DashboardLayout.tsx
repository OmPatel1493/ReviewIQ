import { NavLink, Outlet } from 'react-router-dom'
import { AuthBar } from '@/components/cards'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/search', label: 'Search', end: false },
  { to: '/review', label: 'Review', end: false },
  { to: '/ask', label: 'Ask AI', end: false },
  { to: '/status', label: 'Status', end: false },
]

export default function DashboardLayout() {
  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-indigo-600/20 blur-[120px]" />
        <div className="absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-violet-600/10 blur-[120px]" />
      </div>

      <div className="relative flex min-h-screen">
        {/* Sidebar (desktop) */}
        <aside className="hidden w-56 shrink-0 flex-col border-r border-white/10 px-4 py-6 md:flex">
          <div className="mb-8 flex items-center gap-2 px-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-500 text-sm font-bold text-white shadow-lg shadow-indigo-500/30">
              RQ
            </div>
            <span className="text-lg font-semibold tracking-tight">ReviewIQ</span>
          </div>
          <nav className="flex flex-col gap-1">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive
                      ? 'bg-indigo-500/15 text-indigo-200 ring-1 ring-inset ring-indigo-500/30'
                      : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                  }`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <p className="mt-auto px-2 pt-6 text-xs text-slate-600">
            local-first ($0) AI stack
          </p>
        </aside>

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
            <nav className="flex gap-1 md:hidden">
              {NAV.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    `rounded-lg px-2 py-1 text-xs font-medium ${
                      isActive ? 'text-indigo-300' : 'text-slate-400'
                    }`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
            <div className="hidden md:block" />
            <AuthBar />
          </header>

          <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  )
}
