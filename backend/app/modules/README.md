# Feature modules

Each subpackage is a **bounded context** — a vertical slice of the domain that
owns its own service logic and (later) router. Keeping these separate is what
makes the codebase read like a startup's, not a script:

| Module   | Responsibility                                              | Phase |
| -------- | ----------------------------------------------------------- | ----- |
| `auth`   | JWT issuing/verification + GitHub OAuth login flow          | 2     |
| `github` | GitHub REST/GraphQL client: repos, PRs, commits, diffs      | 3     |
| `search` | Semantic code search over the Qdrant index                  | 5     |
| `review` | The review engine: RAG + LLM → scored, severity-tagged findings | 6 |
| `ai`     | Provider-agnostic LLM + embedding interfaces (Ollama/OpenAI/BGE) | 4/6 |

The cross-cutting layers (`api`, `services`, `repositories`, `models`,
`schemas`, `domain`, `workers`, `utils`) live one level up under `app/`.
