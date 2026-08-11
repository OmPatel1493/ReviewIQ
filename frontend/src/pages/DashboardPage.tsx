import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchAnalytics } from '@/lib/api'
import { ScoreBar } from '@/components/cards'

const SEV_ORDER = ['critical', 'high', 'medium', 'low']
const SEV_FILL: Record<string, string> = {
  critical: 'bg-rose-400',
  high: 'bg-orange-400',
  medium: 'bg-amber-400',
  low: 'bg-sky-400',
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur">
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs font-medium uppercase tracking-wider text-slate-500">{label}</p>
    </div>
  )
}

function BarRow({
  label,
  value,
  max,
  fill,
}: {
  label: string
  value: number
  max: number
  fill: string
}) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="flex items-center gap-3">
      <span className="w-28 shrink-0 text-xs capitalize text-slate-400">
        {label.replace('_', ' ')}
      </span>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${fill}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right text-xs font-medium text-slate-300">{value}</span>
    </div>
  )
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur">
      <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      {children}
    </div>
  )
}

export default function DashboardPage() {
  const q = useQuery({ queryKey: ['analytics'], queryFn: fetchAnalytics, retry: false })

  if (q.isError) {
    return (
      <div>
        <h1 className="mb-6 text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="rounded-lg bg-amber-500/10 p-4 text-sm text-amber-200">
          Sign in with GitHub to see your review analytics.
        </p>
      </div>
    )
  }

  const a = q.data
  const sevMax = a ? Math.max(1, ...Object.values(a.findings_by_severity)) : 1
  const catEntries = a
    ? Object.entries(a.findings_by_category)
        .filter(([, n]) => n > 0)
        .sort((x, y) => y[1] - x[1])
    : []
  const catMax = catEntries.length ? Math.max(1, ...catEntries.map(([, n]) => n)) : 1

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>

      {q.isPending || !a ? (
        <p className="text-sm text-slate-500">Loading analytics…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile label="Repos" value={a.repos_connected} />
            <StatTile label="Indexed" value={a.repos_indexed} />
            <StatTile label="Reviews" value={a.reviews_total} />
            <StatTile label="Findings" value={a.findings_total} />
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="Average scores (completed reviews)">
              <div className="grid gap-3">
                <ScoreBar label="Quality" value={a.score_averages.quality} />
                <ScoreBar label="Security" value={a.score_averages.security} />
                <ScoreBar label="Complexity" value={a.score_averages.complexity} />
                <ScoreBar label="Maintainability" value={a.score_averages.maintainability} />
                <ScoreBar label="Performance" value={a.score_averages.performance} />
              </div>
            </Panel>

            <Panel title="Findings by severity">
              <div className="space-y-2.5">
                {SEV_ORDER.map((s) => (
                  <BarRow
                    key={s}
                    label={s}
                    value={a.findings_by_severity[s] ?? 0}
                    max={sevMax}
                    fill={SEV_FILL[s]}
                  />
                ))}
              </div>
            </Panel>
          </div>

          <Panel title="Findings by category">
            {catEntries.length === 0 ? (
              <p className="text-sm text-slate-500">
                No findings yet — run a review to populate this.
              </p>
            ) : (
              <div className="space-y-2.5">
                {catEntries.map(([c, n]) => (
                  <BarRow key={c} label={c} value={n} max={catMax} fill="bg-indigo-400" />
                ))}
              </div>
            )}
          </Panel>

          <Panel title="Recent reviews">
            {a.recent_reviews.length === 0 ? (
              <p className="text-sm text-slate-500">No reviews yet.</p>
            ) : (
              <ul className="divide-y divide-white/5">
                {a.recent_reviews.map((r) => (
                  <li
                    key={r.id}
                    className="flex items-center justify-between gap-3 py-2.5 text-sm"
                  >
                    <div className="min-w-0 truncate">
                      <span className="font-mono text-indigo-300">
                        {r.repository} #{r.pull_number}
                      </span>
                      <span className="ml-2 text-xs text-slate-500">{r.findings} findings</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      {r.quality_score != null && (
                        <span className="text-xs text-slate-400">Q {r.quality_score}</span>
                      )}
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${
                          r.status === 'completed'
                            ? 'bg-emerald-500/15 text-emerald-300'
                            : r.status === 'failed'
                              ? 'bg-rose-500/15 text-rose-300'
                              : 'bg-slate-500/15 text-slate-300'
                        }`}
                      >
                        {r.status}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </>
      )}
    </div>
  )
}
