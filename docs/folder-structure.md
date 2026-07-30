# Folder structure

```
ReviewIQ/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app factory + lifespan
│   │   ├── core/                  # cross-cutting infra
│   │   │   ├── config.py          #   typed settings (pydantic-settings)
│   │   │   └── logging.py         #   logging setup
│   │   ├── api/
│   │   │   ├── router.py          # stitches feature routers under /api/v1
│   │   │   └── v1/                # versioned endpoints (health, later: auth, repos…)
│   │   ├── domain/                # pure entities & business rules (no framework imports)
│   │   ├── models/                # SQLAlchemy ORM models (Phase 1)
│   │   ├── schemas/               # Pydantic request/response DTOs
│   │   ├── repositories/          # data-access objects over the DB (Phase 1)
│   │   ├── services/              # use-cases / orchestration (business logic)
│   │   ├── workers/               # Celery app + tasks (Phase 4)
│   │   ├── utils/                 # small shared helpers
│   │   └── modules/               # bounded contexts (vertical slices)
│   │       ├── auth/              #   JWT + GitHub OAuth        (Phase 2)
│   │       ├── github/            #   GitHub REST/GraphQL client (Phase 3)
│   │       ├── ai/                #   LLM + embedding providers  (Phase 4/6)
│   │       ├── search/            #   semantic search           (Phase 5)
│   │       └── review/            #   the review engine         (Phase 6)
│   ├── tests/                     # pytest (unit + API)
│   ├── Dockerfile
│   ├── pyproject.toml             # deps + tool config (uv, ruff, mypy, pytest)
│   └── .python-version            # pinned to 3.12
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx               # app bootstrap + QueryClientProvider
│   │   ├── App.tsx                # (Phase 0) live status page
│   │   ├── index.css              # Tailwind entry + base tokens
│   │   └── lib/api.ts             # typed fetch client
│   ├── vite.config.ts             # Tailwind plugin + /api proxy + @ alias
│   └── package.json
│
├── docs/                          # architecture, folder structure, API, deploy
├── interview-notes/               # LOCAL ONLY (gitignored) — rationale + interview prep
├── scripts/                       # dev/ops helper scripts
├── docker-compose.yml             # Postgres · Redis · Qdrant · API
├── Makefile                       # make dev-api / dev-web / test / up …
├── .env.example                   # documented environment template
└── README.md
```

## Conventions

- **One responsibility per file.** A router only routes; a service only orchestrates.
- **Imports point inward.** `api → services → repositories/domain`. Nothing in `domain`
  imports FastAPI or SQLAlchemy.
- **DTOs ≠ ORM models.** Pydantic schemas are the API contract; SQLAlchemy models are the
  storage shape. We map between them deliberately so the DB can change without breaking clients.
- **New feature checklist:** add a module (or extend one) → service method → repository (if new
  data) → router → schema → test → wire into `api/router.py`.
