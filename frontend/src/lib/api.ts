/**
 * Tiny typed fetch client.
 *
 * In dev, requests to `/api/*` are proxied to the FastAPI backend by Vite
 * (see vite.config.ts), so we use relative URLs and never hard-code the host.
 * In Phase 8 this grows into a richer client (auth headers, error envelopes,
 * TanStack Query hooks per resource).
 */

// Allow overriding the base in non-proxied deployments; defaults to same-origin.
const BASE = import.meta.env.VITE_API_BASE ?? ''

export interface HealthResponse {
  status: string
  app: string
  environment: string
  version: string
  time: string
}

export interface ComponentStatus {
  name: string
  status: string
  detail?: string | null
}

export interface ReadinessResponse {
  status: string
  components: ComponentStatus[]
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as T
}

export const fetchHealth = () => getJson<HealthResponse>('/api/v1/health')
export const fetchReadiness = () => getJson<ReadinessResponse>('/api/v1/health/ready')

// ----------------------------------------------------------------- auth ----
export interface UserOut {
  id: string
  github_id: number
  login: string
  name?: string | null
  email?: string | null
  avatar_url?: string | null
  created_at: string
}

/** Current user; throws (401) when not signed in — callers treat that as "logged out". */
export const fetchMe = () => getJson<UserOut>('/api/v1/auth/me')

/** Ask the backend for the GitHub authorize URL. Surfaces the 503 "not configured" case. */
export async function githubLoginUrl(): Promise<
  { ok: true; url: string } | { ok: false; message: string }
> {
  const res = await fetch(`${BASE}/api/v1/auth/github/login`)
  if (res.ok) {
    const data = (await res.json()) as { authorize_url: string }
    return { ok: true, url: data.authorize_url }
  }
  let message = `Sign-in unavailable (${res.status})`
  try {
    const data = (await res.json()) as { detail?: string }
    if (data.detail) message = data.detail
  } catch {
    /* non-JSON error body — keep the generic message */
  }
  return { ok: false, message }
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/api/v1/auth/logout`, { method: 'POST' })
}

// --------------------------------------------------------------- repos ----
export interface RepositorySummary {
  id: string
  full_name: string
  index_status: string
  indexed_at?: string | null
}

/** Repositories the signed-in user has connected. Throws 401 when logged out. */
export const fetchRepositories = () =>
  getJson<RepositorySummary[]>('/api/v1/repos')

// -------------------------------------------------------------- search ----
export interface SearchResultItem {
  file_path: string
  start_line: number
  end_line: number
  content: string
  score: number
}

export interface SearchResponse {
  repository_id: string
  query: string
  results: SearchResultItem[]
}

/** Semantic code search scoped to one connected repository. */
export async function searchCode(
  repositoryId: string,
  query: string,
  limit?: number,
): Promise<SearchResponse> {
  const res = await fetch(`${BASE}/api/v1/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_id: repositoryId, query, limit }),
  })
  if (!res.ok) {
    throw new Error(`Search failed: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as SearchResponse
}

// -------------------------------------------------------------- reviews ----
export interface JobStatusOut {
  id: string
  type: string
  status: string // queued | running | succeeded | failed
  progress: number
  error?: string | null
  result?: Record<string, unknown> | null
}

export interface ReviewCreatedOut {
  review_id: string
  job_id: string
}

export interface FindingOut {
  id: string
  file_path: string
  line_start: number | null
  line_end: number | null
  severity: string
  category: string
  title: string
  rationale: string
  impact: string | null
  suggestion: string | null
  confidence: number | null
}

export interface ReviewOut {
  id: string
  pull_request_id: string
  status: string
  summary: string | null
  quality_score: number | null
  security_score: number | null
  complexity_score: number | null
  maintainability_score: number | null
  performance_score: number | null
  provider: string | null
  model: string | null
  created_at: string
  completed_at: string | null
  findings: FindingOut[]
}

/** Kick off an AI review of a PR. Returns ids to poll the job + fetch the review. */
export async function triggerReview(
  repositoryId: string,
  pullNumber: number,
): Promise<ReviewCreatedOut> {
  const res = await fetch(`${BASE}/api/v1/reviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repository_id: repositoryId, pull_number: pullNumber }),
  })
  if (!res.ok) {
    throw new Error(`Review request failed: ${res.status} ${res.statusText}`)
  }
  return (await res.json()) as ReviewCreatedOut
}

export const fetchJob = (jobId: string) => getJson<JobStatusOut>(`/api/v1/jobs/${jobId}`)
export const fetchReview = (reviewId: string) =>
  getJson<ReviewOut>(`/api/v1/reviews/${reviewId}`)
