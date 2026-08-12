# Phase 9 — CI/CD + deploy

> Status: 🚧 engineering complete (CI + deploy-readiness shipped); live deployment is a
> documented, operator-driven step. This phase makes ReviewIQ deployable at **$0** and keeps
> `main` green.

## What shipped

- **CI** — `.github/workflows/ci.yml`: on every push to `main` and every PR, a **backend**
  job runs `ruff` + `mypy` + `pytest`, and a **frontend** job runs `oxlint` + `tsc`/build.
  Hermetic — no services needed (tests stub the DB, fake GitHub/Qdrant/LLM).
- **Hosted-LLM provider** — `app/modules/ai/llm.py`: `OpenAICompatibleProvider` speaks the
  OpenAI chat API, so `AI_PROVIDER=openai` can point at **any** OpenAI-compatible endpoint.
  A local 7B model can't run on free hosting, so in production you point it at a **free**
  hosted API (**Groq**) with a base URL + key + model. Ollama stays the local default.
- **SPA routing fallback** — `frontend/vercel.json` + `frontend/public/_redirects` route all
  paths to `index.html`, so deep links / refreshes on `/search`, `/review`, … work on a static
  host (needed since Phase 8 added client-side routing).
- **Hermetic tests** — `tests/conftest.py` forces the OAuth env empty so the suite never
  depends on a developer's real `.env`.

## The $0 architecture (each piece → a free tier)

| Piece | Free host | Notes |
| --- | --- | --- |
| Frontend (static SPA) | **Vercel** or **Cloudflare Pages** | build `frontend`; set `VITE_API_BASE` to the API URL |
| Backend API | **Render** / **Fly.io** / **HF Spaces** (Docker) | builds `backend/Dockerfile` |
| Worker (Celery) | same host (2nd process) — or **EAGER mode** | `CELERY_TASK_ALWAYS_EAGER=true` runs jobs inline, no worker |
| Postgres | **Neon** or **Supabase** | set `POSTGRES_*` (or a single DSN) |
| Redis | **Upstash** | Celery broker + cache |
| Qdrant | **Qdrant Cloud** (free 1 GB) | set `QDRANT_HOST`/`QDRANT_PORT` (+ API key) |
| LLM | **Groq** (free) | `AI_PROVIDER=openai`, `OPENAI_BASE_URL=https://api.groq.com/openai/v1` |
| Embeddings | runs on the API host CPU | fastembed BGE-small — tiny, no extra service |

**Worker trade-off:** free tiers rarely give you a second always-on process. Simplest $0 path
is `CELERY_TASK_ALWAYS_EAGER=true` — indexing/reviews run **inline** in the request (slower, can
time out on big jobs, fine for a low-traffic demo). If the host allows a second process, run the
real worker instead for a responsive API.

## Deploy checklist (operator steps)

1. **Managed data**: create Neon (Postgres), Upstash (Redis), Qdrant Cloud (free) — copy their
   connection details.
2. **LLM**: create a Groq API key.
3. **GitHub OAuth (prod)**: new OAuth App with your real domain — Homepage `https://<frontend>`,
   callback `https://<api>/api/v1/auth/github/callback`.
4. **Backend**: deploy `backend/` (Docker) to your host; set env vars — the `POSTGRES_*`,
   `REDIS_*`, `QDRANT_*`, `GITHUB_CLIENT_ID/SECRET`, a strong `JWT_SECRET`, `ENCRYPTION_KEY`,
   `COOKIE_SECURE=true`, `CORS_ORIGINS=https://<frontend>`, `AI_PROVIDER=openai`,
   `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `OPENAI_API_KEY`, `OPENAI_MODEL`. Run
   `alembic upgrade head` once.
5. **Frontend**: deploy `frontend/` to Vercel/Pages with `VITE_API_BASE=https://<api>` at build
   time. The SPA fallback is already configured.
6. Open the site, sign in, connect + index a repo, run a review.

## Design choices
- **Provider interface pays off at deploy**: swapping the local model for a free hosted API is
  a config change (`AI_PROVIDER=openai` + Groq URL/key) — no code edits — exactly what the
  interface was built for.
- **Secrets only via host env vars**: never in the image or repo. `.env` stays local; production
  reads real environment variables (which pydantic-settings prioritises over any dotenv file).
- **CI is hermetic**: it runs the same `ruff`/`mypy`/`pytest`/`build` you run locally, with no
  external services, so it's fast and never flaky.
- **EAGER as the $0 escape hatch**: a demo can run without a dedicated worker dyno by executing
  jobs inline — a deliberate trade of latency for cost.
