# Phase 0 — Monorepo scaffold

> Status: ✅ complete. This document is the permanent record of what Phase 0
> delivered, **every command** to run it, the **free-tier tools** it uses, and
> **what we'd upgrade to with a budget** for more performance.

## What shipped

- **Backend** (`backend/`): FastAPI app-factory (`app/main.py`), typed settings
  (`app/core/config.py`), logging (`app/core/logging.py`), health + readiness
  endpoints, auto-generated OpenAPI docs at `/docs`, and a Clean-Architecture
  folder layout (`api / services / repositories / domain / models / schemas /
  workers / modules`).
- **Frontend** (`frontend/`): React 19 + TypeScript + Vite 8, Tailwind v4,
  TanStack Query, a typed API client, and a live status page that reaches the
  backend through a dev proxy.
- **Infra & docs**: `docker-compose.yml` (Postgres + Redis + Qdrant + API),
  `Makefile`, `.env.example`, `docs/`, and the local-only `interview-notes/`.

**Verification:** backend `ruff` clean + 4/4 tests; frontend type-checks + builds;
live SPA reaches the API with zero console errors.

---

## Tools we use — and why the free tier is enough (for now)

| Tool | Role in ReviewIQ | Cost | Why the free option is fine at this stage |
| --- | --- | --- | --- |
| **uv** | Python package/venv/lock manager | Free (OSS) | Fastest reliable installer; single tool for envs + lockfile |
| **FastAPI / Uvicorn** | Web framework + ASGI server | Free (OSS) | Handles our concurrency needs on one process locally |
| **PostgreSQL 16** | Relational database | Free (OSS) | Full-featured; a local container is plenty for dev |
| **Redis 7** | Celery broker + cache | Free (OSS) | In-memory, trivial to self-host |
| **Qdrant** | Vector database (search/RAG) | Free (OSS) | Runs in one container; no per-query cost |
| **Ollama** | Local LLM runtime *(from Phase 4/6)* | Free (OSS) | $0 inference on your own machine; provider is swappable |
| **BGE/E5 (sentence-transformers)** | Embeddings *(from Phase 4)* | Free (OSS) | Strong open models; run on CPU |
| **React + Vite + Tailwind + shadcn** | Frontend | Free (OSS) | Industry-standard SaaS UI stack |
| **Docker / Compose** | Local orchestration | Free (Desktop for personal/student use) | One command brings up the whole stack |
| **GitHub Actions** *(Phase 9)* | CI/CD | Free tier (public repos / limited private minutes) | Lint+test+build fits comfortably in free minutes |

**Guiding principle:** everything runs at **$0** on a student machine. The AI
providers sit behind interfaces (`LLMProvider`, `EmbeddingProvider`), so moving to
a paid, higher-quality provider is a config change — never a rewrite.

---

## Command reference (everything you need to run Phase 0)

### One-time setup
```bash
cd ReviewIQ
cp .env.example .env                 # then edit secrets as needed

# Backend deps (creates backend/.venv, writes uv.lock)
cd backend && uv sync && cd ..

# Frontend deps
cd frontend && npm install && cd ..
```
Or from the repo root in one shot: `make install`.

### Run the app locally (two terminals)
```bash
# Terminal 1 — API with autoreload → http://localhost:8000  (docs at /docs)
make dev-api          # == cd backend && uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — SPA → http://localhost:5173
make dev-web          # == cd frontend && npm run dev
```

### Quality gates
```bash
make test             # backend: uv run pytest
make lint             # backend: ruff + mypy ; frontend: npm run lint
make fmt              # backend: ruff format + ruff --fix
```

### Full stack with Docker
```bash
make up               # docker compose up -d  (Postgres + Redis + Qdrant + API)
make ps               # docker compose ps
make logs             # tail logs
make down             # stop everything
make build            # rebuild images
```

### Handy one-offs
```bash
# Verify the API without a browser
curl -s http://localhost:8000/api/v1/health | python -m json.tool

# Frontend production build (type-check + bundle)
cd frontend && npm run build

# See all Make targets
make help
```

### Git (you commit — the repo is already `git init`'d on `main`)
```bash
git status            # interview-notes/, .env, .venv, node_modules are ignored
git add .
git commit -m "Phase 0: monorepo scaffold"
```

---

## If we had a budget: performance & scale upgrades

None of these are needed to build or demo ReviewIQ — but this is the map we'd
follow to make it faster and production-grade **with funding**. (Great interview
material: it shows you know where the free tier ends.)

| Concern | Free choice (now) | Funded upgrade | Performance / benefit |
| --- | --- | --- | --- |
| **LLM quality/latency** | Ollama local (`qwen2.5-coder`) | **OpenAI GPT-4o / Anthropic Claude** (or a GPU host like Modal/Runpod/Together) | Much stronger reasoning, faster, no local RAM/CPU load; better, more reliable reviews |
| **Embeddings** | BGE/E5 on CPU | **OpenAI `text-embedding-3`** or GPU-served BGE-large | Higher recall + faster batch indexing of big repos |
| **Vector DB** | Self-hosted Qdrant container | **Qdrant Cloud** / **Pinecone** | Managed HA, snapshots, higher throughput, no ops |
| **Database** | Local Postgres container | **Managed Postgres** (Neon / RDS / Cloud SQL) with read replicas + PgBouncer | Backups, failover, connection pooling, scale reads |
| **Cache / broker** | Local Redis container | **Managed Redis** (Upstash / ElastiCache) | Persistence, HA, no ops |
| **Workers** | Celery on one machine | **Autoscaling worker pool** (K8s / ECS / Fly Machines) | Parallelize indexing + reviews across many nodes |
| **Frontend hosting** | Vite dev / static build | **CDN** (Cloudflare Pages / Vercel) | Global edge caching, instant loads |
| **Observability** | stdout logs | **Sentry + OpenTelemetry + Grafana** | Error tracking, tracing, dashboards |
| **CI/CD** | GitHub Actions free minutes | **Paid runners / larger matrix** | Faster pipelines, parallel test shards |
| **GitHub integration** | OAuth + polling | **GitHub App + webhooks** | Auto-trigger reviews on PR open; higher rate limits |

**Cost-control note:** even with a budget we'd keep the provider abstraction and
cache aggressively (skip re-embedding unchanged files, memoize GitHub responses),
so paid API spend scales with *new* work, not repeated work.
