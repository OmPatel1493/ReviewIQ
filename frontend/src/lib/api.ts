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
