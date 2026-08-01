import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchHealth,
  fetchMe,
  fetchReadiness,
  githubLoginUrl,
  logout,
  type ComponentStatus,
  type HealthResponse,
  type ReadinessResponse,
} from '@/lib/api'

/** The build roadmap — Phase 0 is what we're shipping right now. */
const PHASES: { n: number; label: string }[] = [
  { n: 0, label: 'Scaffold' },
  { n: 1, label: 'Data model' },
  { n: 2, label: 'Auth + OAuth' },
  { n: 3, label: 'GitHub' },
  { n: 4, label: 'Indexing' },
  { n: 5, label: 'Search' },
  { n: 6, label: 'Review engine' },
  { n: 7, label: 'Ask AI' },
  { n: 8, label: 'Dashboard UI' },
  { n: 9, label: 'CI/CD + deploy' },
]

const CURRENT_PHASE = 4

function StatusDot({ tone }: { tone: 'ok' | 'error' | 'idle' }) {
  const color =
    tone === 'ok'
      ? 'bg-emerald-400'
      : tone === 'error'
        ? 'bg-rose-400'
        : 'bg-amber-400'
  return (
    <span className="relative flex h-2.5 w-2.5">
      {tone === 'ok' && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/70" />
      )}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${color}`} />
    </span>
  )
}

function ComponentBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    ok: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    error: 'bg-rose-500/15 text-rose-300 ring-rose-500/30',
    skipped: 'bg-slate-500/15 text-slate-300 ring-slate-500/30',
  }
  const cls = map[status] ?? map.skipped
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      {status}
    </span>
  )
}

function BackendCard() {
  const health = useQuery<HealthResponse>({ queryKey: ['health'], queryFn: fetchHealth })
  const readiness = useQuery<ReadinessResponse>({
    queryKey: ['readiness'],
    queryFn: fetchReadiness,
  })

  const tone: 'ok' | 'error' | 'idle' = health.isPending
    ? 'idle'
    : health.isError
      ? 'error'
      : 'ok'

  const label = health.isPending
    ? 'Checking backend…'
    : health.isError
      ? 'Backend unreachable'
      : 'Backend online'

  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusDot tone={tone} />
          <span className="text-sm font-medium text-slate-200">{label}</span>
        </div>
        <button
          type="button"
          onClick={() => {
            void health.refetch()
            void readiness.refetch()
          }}
          className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-300 transition hover:border-white/25 hover:text-white"
        >
          Refresh
        </button>
      </div>

      {health.data && (
        <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <div>
            <dt className="text-slate-500">Service</dt>
            <dd className="font-medium text-slate-100">{health.data.app}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Version</dt>
            <dd className="font-medium text-slate-100">v{health.data.version}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Environment</dt>
            <dd className="font-medium text-slate-100">{health.data.environment}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Status</dt>
            <dd className="font-medium text-emerald-300">{health.data.status}</dd>
          </div>
        </dl>
      )}

      {health.isError && (
        <p className="mt-5 rounded-lg bg-rose-500/10 p-3 text-sm text-rose-200">
          Could not reach <code className="font-mono">/api/v1/health</code>. Start the backend
          with <code className="font-mono">make dev-api</code> and this panel goes green.
        </p>
      )}

      <div className="mt-6">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Dependencies
        </p>
        <ul className="space-y-2">
          {(readiness.data?.components ?? placeholderComponents).map((c: ComponentStatus) => (
            <li
              key={c.name}
              className="flex items-center justify-between rounded-lg bg-white/[0.02] px-3 py-2"
            >
              <div className="flex flex-col">
                <span className="text-sm font-medium capitalize text-slate-200">{c.name}</span>
                {c.detail && <span className="text-xs text-slate-500">{c.detail}</span>}
              </div>
              <ComponentBadge status={c.status} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}

const placeholderComponents: ComponentStatus[] = [
  { name: 'postgres', status: 'skipped', detail: 'wired in Phase 1' },
  { name: 'redis', status: 'skipped', detail: 'wired in Phase 4' },
  { name: 'qdrant', status: 'skipped', detail: 'wired in Phase 4' },
]

function RoadmapCard() {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur">
      <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Build roadmap
      </p>
      <ol className="space-y-2">
        {PHASES.map((p) => {
          const done = p.n < CURRENT_PHASE
          const current = p.n === CURRENT_PHASE
          return (
            <li key={p.n} className="flex items-center gap-3">
              <span
                className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                  current
                    ? 'bg-gradient-to-br from-indigo-500 to-violet-500 text-white'
                    : done
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-white/5 text-slate-500'
                }`}
              >
                {p.n}
              </span>
              <span
                className={`text-sm ${
                  current ? 'font-semibold text-white' : done ? 'text-slate-300' : 'text-slate-500'
                }`}
              >
                {p.label}
              </span>
              {current && (
                <span className="ml-auto rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs font-medium text-indigo-300 ring-1 ring-inset ring-indigo-500/30">
                  in progress
                </span>
              )}
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function GitHubMark() {
  return (
    <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="currentColor">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z" />
    </svg>
  )
}

function AuthBar() {
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ['me'], queryFn: fetchMe, retry: false })
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function signIn() {
    setMessage(null)
    setBusy(true)
    const result = await githubLoginUrl()
    if (result.ok) {
      window.location.href = result.url
    } else {
      setMessage(result.message)
      setBusy(false)
    }
  }

  async function signOut() {
    await logout()
    await queryClient.invalidateQueries({ queryKey: ['me'] })
  }

  if (me.data) {
    return (
      <div className="flex items-center gap-3">
        {me.data.avatar_url && (
          <img
            src={me.data.avatar_url}
            alt=""
            className="h-8 w-8 rounded-full ring-1 ring-white/20"
          />
        )}
        <span className="text-sm font-medium text-slate-200">@{me.data.login}</span>
        <button
          type="button"
          onClick={signOut}
          className="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-slate-300 transition hover:border-white/25 hover:text-white"
        >
          Sign out
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <button
        type="button"
        onClick={signIn}
        disabled={busy}
        className="inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-200 disabled:opacity-60"
      >
        <GitHubMark />
        {busy ? 'Redirecting…' : 'Sign in with GitHub'}
      </button>
      {message && (
        <p className="max-w-xs text-right text-xs text-amber-300/90">{message}</p>
      )}
    </div>
  )
}

export default function App() {
  return (
    <div className="min-h-full bg-slate-950 text-slate-100">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-indigo-600/20 blur-[120px]" />
        <div className="absolute bottom-0 right-0 h-[28rem] w-[28rem] rounded-full bg-violet-600/10 blur-[120px]" />
      </div>

      <main className="relative mx-auto flex max-w-5xl flex-col px-6 py-16">
        <div className="absolute right-6 top-6 z-10">
          <AuthBar />
        </div>

        <header className="mb-12 flex flex-col items-center text-center">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 font-bold text-white shadow-lg shadow-indigo-500/30">
              RQ
            </div>
            <span className="text-2xl font-semibold tracking-tight">ReviewIQ</span>
          </div>
          <h1 className="mt-8 max-w-2xl bg-gradient-to-b from-white to-slate-400 bg-clip-text text-4xl font-bold leading-tight tracking-tight text-transparent sm:text-5xl">
            AI code review that reads pull requests like a senior engineer
          </h1>
          <p className="mt-4 max-w-xl text-balance text-slate-400">
            Indexes your repository, understands the diff with RAG, and posts scored,
            severity-tagged feedback — bugs, security, performance, and maintainability.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <a
              href="/docs"
              className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900 transition hover:bg-slate-200"
            >
              API docs →
            </a>
            <a
              href="/redoc"
              className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-slate-200 transition hover:border-white/30"
            >
              ReDoc
            </a>
          </div>
        </header>

        <section className="grid gap-6 md:grid-cols-2">
          <BackendCard />
          <RoadmapCard />
        </section>

        <footer className="mt-12 text-center text-xs text-slate-600">
          Phase 4 · indexing pipeline · FastAPI + React · local-first ($0) AI stack
        </footer>
      </main>
    </div>
  )
}
