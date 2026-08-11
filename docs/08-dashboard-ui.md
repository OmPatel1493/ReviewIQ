# Phase 8 — Dashboard UI + analytics

> Status: ✅ complete. The single-page demo becomes a real, routed SaaS dashboard: a
> sidebar shell, dedicated pages for each tool, and an analytics overview that aggregates
> the user's reviews and findings.

## What shipped

- **Analytics API** — `app/modules/analytics/`: `AnalyticsService` aggregates everything
  scoped to the user's repos (joined Repository → PullRequest → Review → Finding): repo/
  review/finding counts, findings grouped by severity and category (every enum value seeded
  to 0 so bars always render), mean 0–100 scores across completed reviews, and the 5 most
  recent reviews. Exposed at `GET /api/v1/analytics/overview`.
- **Routed frontend** — added **react-router**. `main.tsx` wraps the app in `BrowserRouter`;
  `App.tsx` is now a route table under a `DashboardLayout` (sidebar + top bar + `Outlet`).
- **Pages** — `/` dashboard (analytics), `/search`, `/review`, `/ask`, `/status`. The tool
  cards were extracted from the monolithic `App.tsx` into `components/cards.tsx` and are now
  reused as pages.
- **Dashboard** — `pages/DashboardPage.tsx`: stat tiles (repos / indexed / reviews / findings),
  average-score bars, findings-by-severity and findings-by-category bar charts (pure CSS/SVG —
  no chart dependency), and a recent-reviews list. Roadmap advanced to Phase 8.

  | Method | Path | Purpose |
  | ------ | ---- | ------- |
  | GET | `/api/v1/analytics/overview` | Aggregate dashboard stats for the signed-in user |

**Verification:** `ruff` + `mypy` clean (81 source files); **69/69** tests (analytics route
auth-gating added; the aggregation is DB-heavy so it's covered by the integration path, not the
hermetic suite). Frontend `oxlint` clean and `tsc -b && vite build` green; the dev server serves
the dashboard at `/` and the tool routes (`/search`, `/review`, `/ask`, `/status`) render and
navigate correctly (logged-out, they degrade to a "sign in" prompt). No new migration.

## Layout

```
BrowserRouter
└─ DashboardLayout (sidebar nav + header + AuthBar)
   ├─ /          DashboardPage   → GET /analytics/overview → tiles + charts + recent reviews
   ├─ /search    SearchCard
   ├─ /review    ReviewCard
   ├─ /ask       AskCard
   └─ /status    BackendCard + RoadmapCard
```

## Run it
```bash
docker compose up -d db redis qdrant
cd backend && uv run alembic upgrade head          # no new migration in P8
uv run uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev                          # http://localhost:5173
```
Sign in; the dashboard fills in as you connect repos and run reviews. Hermetic tests:
`cd backend && uv run pytest -q`.

## Design choices
- **One analytics endpoint, not many**: the dashboard needs a coherent snapshot, so a single
  aggregate query set beats N round-trips. All counts are scoped by `Repository.owner_id`.
- **Seed every enum bucket to 0**: the severity/category charts always render the full set of
  bars, so an empty repo shows a clean zeroed chart instead of a collapsed one.
- **CSS/SVG charts, no library**: bars are a few divs — keeps the bundle small and the theme
  consistent, and avoids a dependency for what is genuinely simple. (A chart lib is easy to add
  later if the analytics grow.)
- **Extract, then route**: the tool cards moved into `components/cards.tsx` unchanged and are
  reused as pages — routing was added around existing, tested UI rather than a rewrite.
- **404 → dashboard**: an unknown path renders the dashboard rather than a dead end.
