# Phase 3 — GitHub module (repos, PRs, commits, diffs)

> Status: ✅ complete. The data-ingestion layer: pull real repositories and pull
> requests from GitHub into ReviewIQ, using each user's encrypted OAuth token.

## What shipped

- **Authenticated GitHub client** (`app/modules/github/client.py`) — one class owns
  auth, **pagination** (follows `Link: rel="next"`), API versioning, and error/
  rate-limit handling. Injectable `httpx.AsyncClient` makes it fully testable.
- **Typed GitHub schemas** (`schemas.py`) — validate GitHub JSON into Pydantic models
  at the boundary (repos, PRs, files, commits); a GitHub change fails loudly here.
- **Repositories** — `RepositoryRepository`, `PullRequestRepository`,
  `ActivityLogRepository` (data access, upsert-by-GitHub-id).
- **`GitHubService`** — connect a repo, list connectable/connected repos, **sync PRs**,
  fetch a PR's changed files+diffs; enforces per-user ownership; records activity.
- **Endpoints** (`/api/v1/repos`, all auth-gated):
  | Method | Path | Purpose |
  | --- | --- | --- |
  | GET | `/repos/github` | List the user's GitHub repos (connectable) |
  | GET | `/repos` | List connected repos (from DB) |
  | POST | `/repos/connect` | Connect `owner/repo` |
  | GET | `/repos/{id}` | Get a connected repo |
  | GET | `/repos/{id}/pulls` | Sync + list the repo's PRs |
  | GET | `/repos/{id}/pulls/{n}/files` | Changed files + diffs for a PR |

**Verification:** `ruff` + `mypy` clean; **40/40** unit tests (client pagination,
merged-state derivation, diff parsing, rate-limit + error mapping, and auth-gating on
every route via `httpx.MockTransport`); a full **end-to-end run vs real Postgres**
(GitHub mocked): connect → sync PRs (`{1: open, 2: merged}`) → read files → activity
logged → `GET /api/v1/repos` serves the persisted repo behind auth.

## Two fixes the integration test caught (worth knowing)

1. **Timezone-aware timestamps.** GitHub returns tz-aware datetimes, but our datetime
   columns were `TIMESTAMP WITHOUT TIME ZONE`, so inserts failed. Converted **all**
   datetime columns to `TIMESTAMPTZ` (`DateTime(timezone=True)`) — best practice, and it
   fixed the insert. New migration: `..._use_timezone_aware_timestamps.py`.
2. **Audit-trail preservation.** `User.activity_logs` had `cascade="all, delete-orphan"`,
   which would delete a user's logs — contradicting the DB's `ON DELETE SET NULL` and the
   "keep the audit trail" intent. Switched to `passive_deletes=True` so the DB sets
   `user_id = NULL` and the log survives.

## Design choices
- **Upsert by GitHub numeric id**, not name — repos/PRs renamed on GitHub don't duplicate.
- **Diffs are fetched live, not stored** — they're an input to the review engine
  (Phase 6), cheap to re-fetch, and can be large; we avoid bloating the DB.
- **GitHub errors → HTTP 502** (we're a healthy gateway to a failing upstream);
  ownership violations → 403; missing repo → 404.
- **Token decrypted just-in-time** per request to build the client; never logged/returned.

## Try it (once GitHub OAuth is configured)
Log in via GitHub, then in Swagger (`/docs`): `GET /repos/github` to see your repos →
`POST /repos/connect {"full_name":"you/your-repo"}` → `GET /repos` →
`GET /repos/{id}/pulls`. The Repositories **UI** lands with the dashboard in Phase 8.
