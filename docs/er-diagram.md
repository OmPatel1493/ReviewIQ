# Entity–Relationship diagram

The relational core of ReviewIQ. One user connects many repositories; each repo has
many pull requests; each PR gets one or more reviews; each review produces many
findings. Repositories also own their indexed code chunks and background jobs.

```mermaid
erDiagram
    users ||--o{ repositories : owns
    users ||--o{ activity_logs : generates
    repositories ||--o{ pull_requests : has
    repositories ||--o{ code_chunks : indexes
    repositories ||--o{ jobs : "schedules"
    pull_requests ||--o{ reviews : receives
    pull_requests ||--o{ jobs : "schedules"
    reviews ||--o{ findings : contains

    users {
        uuid id PK
        bigint github_id UK "GitHub numeric id"
        string login UK
        string name
        string email
        string github_access_token "encrypted, server-only"
        timestamp created_at
    }
    repositories {
        uuid id PK
        uuid owner_id FK
        bigint github_id
        string full_name "owner/repo"
        bool private
        string default_branch
        enum index_status "pending|indexing|indexed|failed"
        timestamp indexed_at
    }
    pull_requests {
        uuid id PK
        uuid repository_id FK
        int number "unique per repo"
        string title
        enum state "open|closed|merged"
        string head_sha
        string base_sha
        int additions
        int deletions
    }
    reviews {
        uuid id PK
        uuid pull_request_id FK
        enum status "pending|running|completed|failed"
        text summary
        int quality_score
        int security_score
        int complexity_score
        int maintainability_score
        int performance_score
        jsonb meta
    }
    findings {
        uuid id PK
        uuid review_id FK
        string file_path
        int line_start
        int line_end
        enum severity "low|medium|high|critical"
        enum category "bug|security|performance|..."
        text rationale "the why"
        text suggestion "suggested fix"
        float confidence
    }
    code_chunks {
        uuid id PK
        uuid repository_id FK
        string file_path
        string symbol
        int start_line
        int end_line
        string content_hash "change detection"
        uuid vector_id "Qdrant point id"
    }
    jobs {
        uuid id PK
        uuid repository_id FK "nullable"
        uuid pull_request_id FK "nullable"
        enum type "clone|index|review|report"
        enum status "queued|running|succeeded|failed"
        int progress "0-100"
        jsonb payload
        jsonb result
    }
    activity_logs {
        uuid id PK
        uuid user_id FK "nullable"
        string action "repo.connected, ..."
        string entity_type
        string entity_id
        jsonb meta
        timestamp created_at
    }
```

## Cardinality & delete rules

| Relationship | Cardinality | On delete |
| --- | --- | --- |
| user → repositories | 1 : N | CASCADE (removing a user removes their repos + everything under them) |
| repository → pull_requests | 1 : N | CASCADE |
| pull_request → reviews | 1 : N | CASCADE |
| review → findings | 1 : N | CASCADE |
| repository → code_chunks | 1 : N | CASCADE (re-index replaces them) |
| repository / pull_request → jobs | 1 : N | CASCADE |
| user → activity_logs | 1 : N | SET NULL (keep the audit trail even if the user is deleted) |

## Notes on design choices

- **UUID primary keys** everywhere — no leaked counts, safe to generate app-side.
- **Native PostgreSQL enums** (`index_status`, `pr_state`, `review_status`, `severity`,
  `finding_category`, `job_type`, `job_status`) give DB-level validation.
- **JSONB** columns (`reviews.meta`, `jobs.payload/result`, `activity_logs.meta`) hold
  flexible, semi-structured data while staying queryable/indexable.
- **`code_chunks.vector_id`** links a relational row to its vector in Qdrant; the float
  vectors themselves live in Qdrant, not Postgres.
- **`content_hash`** enables skipping re-embedding of unchanged code — the biggest cost
  lever in the indexing pipeline.
- **Indexes** on every foreign key and on hot filter columns (`state`, `severity`,
  `category`, `index_status`, `content_hash`, `celery_task_id`).
