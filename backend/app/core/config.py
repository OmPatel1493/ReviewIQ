"""Application configuration.

All runtime configuration lives here in a single, typed `Settings` object built
on `pydantic-settings`. Values are loaded (in priority order) from:

    1. Real environment variables (what Docker / the cloud injects)
    2. A local `.env` file (developer convenience — never committed)
    3. The defaults defined below (safe for local dev, insecure for prod)

Why centralise config?
    * Type-safety: a mistyped port or missing URL fails fast at startup, not at
      the first request.
    * Testability: tests can build `Settings(...)` with overrides.
    * 12-factor: config comes from the environment, so the same image runs in
      local / staging / prod without code changes.

`get_settings()` is cached so the `.env` file is parsed exactly once per process.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ignore unknown keys so one .env can serve many services
    )

    # ------------------------------------------------------------------ App --
    APP_NAME: str = "ReviewIQ"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["local", "dev", "staging", "production"] = "local"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # CORS origins are stored as a comma-separated string (env-friendly) and
    # exposed as a parsed list via `cors_origins`. This avoids pydantic-settings'
    # requirement that list-typed env vars be valid JSON.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ------------------------------------------------------- Security (P2) --
    JWT_SECRET: str = "dev-insecure-change-me-generate-a-real-secret-in-prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # Fernet key (urlsafe base64, 32 bytes) used to encrypt GitHub tokens at rest.
    # If left blank we derive a stable key from JWT_SECRET — fine for dev, but set
    # a real ENCRYPTION_KEY in production (rotating it invalidates stored tokens).
    ENCRYPTION_KEY: str = ""

    # Session cookie that carries our JWT to the browser (httpOnly = XSS-safe).
    COOKIE_NAME: str = "reviewiq_token"
    COOKIE_SECURE: bool = False  # True in prod (HTTPS only)
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    # -------------------------------------------------- GitHub OAuth (P2/3) --
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_CALLBACK_URL: str = "http://localhost:8000/api/v1/auth/github/callback"
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_OAUTH_SCOPES: str = "read:user user:email repo"
    # Where the frontend lives, so the OAuth flow can redirect back to the SPA.
    FRONTEND_URL: str = "http://localhost:5173"

    # --------------------------------------------------------- Postgres (P1) --
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "reviewiq"
    POSTGRES_PASSWORD: str = "reviewiq"
    POSTGRES_DB: str = "reviewiq"
    # Echo every SQL statement to the log — great for debugging, noisy otherwise.
    DB_ECHO: bool = False

    # ------------------------------------------------------------ Redis (P4) --
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # ----------------------------------------------------------- Qdrant (P4) --
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "reviewiq_code_chunks"

    # ----------------------------------------------- Semantic search (P5) --
    # Default number of nearest code chunks a search returns; callers may
    # override per-request (bounded in the request schema).
    SEARCH_TOP_K: int = 10

    # ------------------------------------------------- Review engine (P6) --
    # Bound the work (and the prompt size / cost) of a single PR review.
    REVIEW_MAX_FILES: int = 12          # analyse at most this many changed files
    REVIEW_MAX_PATCH_CHARS: int = 6000  # truncate a file's diff to this many chars
    REVIEW_CONTEXT_TOP_K: int = 3       # RAG snippets retrieved per changed file
    REVIEW_TIMEOUT_SECONDS: float = 180.0  # per LLM call (reviews are slow, local CPU)

    # ---------------------------------------------------------- Ask-AI (P7) --
    ASK_CONTEXT_TOP_K: int = 6          # RAG snippets retrieved to ground an answer

    # -------------------------------------------------- AI providers (P4/6) --
    # Local-first by default (zero API cost). Swap AI_PROVIDER=openai + a key to
    # use OpenAI without touching code.
    AI_PROVIDER: Literal["ollama", "openai"] = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OPENAI_API_KEY: str = ""
    # OpenAI-compatible base URL. Swap to a free hosted API when deployed (Ollama can't
    # run on free tiers) — e.g. Groq: https://api.groq.com/openai/v1
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    EMBEDDING_PROVIDER: Literal["local", "openai"] = "local"
    # BGE / E5 are strong open embedding models; small = fast on CPU.
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    EMBEDDING_DIM: int = Field(default=384, description="Vector size stored in Qdrant")
    EMBED_BATCH_SIZE: int = 64

    # ----------------------------------------------- Celery workers (P4) --
    # Broker + result backend both ride on Redis. EAGER runs tasks inline (no
    # worker) — handy for tests and quick local runs.
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # ------------------------------------------------ Indexing pipeline (P4) --
    CLONE_DIR: str = "/tmp/reviewiq-clones"
    # Only embed source files we understand; skip everything else.
    INDEX_INCLUDE_EXTENSIONS: str = (
        ".py,.js,.jsx,.ts,.tsx,.java,.go,.rb,.rs,.c,.cc,.cpp,.h,.hpp,.cs,"
        ".php,.kt,.swift,.scala,.sh,.sql,.md,.yaml,.yml,.toml"
    )
    INDEX_EXCLUDE_DIRS: str = (
        ".git,node_modules,.venv,venv,dist,build,__pycache__,.next,.mypy_cache,"
        ".ruff_cache,.pytest_cache,target,vendor"
    )
    INDEX_MAX_FILE_BYTES: int = 200_000  # skip huge/generated files
    CHUNK_MAX_LINES: int = 60
    CHUNK_OVERLAP_LINES: int = 10

    # --------------------------------------------------------------- Helpers --
    @property
    def cors_origins(self) -> list[str]:
        """Parse the comma-separated CORS string into a clean list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def github_oauth_scopes(self) -> list[str]:
        return [s.strip() for s in self.GITHUB_OAUTH_SCOPES.split() if s.strip()]

    @property
    def index_include_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.INDEX_INCLUDE_EXTENSIONS.split(",") if e.strip()}

    @property
    def index_exclude_dirs(self) -> set[str]:
        return {d.strip() for d in self.INDEX_EXCLUDE_DIRS.split(",") if d.strip()}

    @property
    def fernet_key(self) -> bytes:
        """A valid Fernet key: use ENCRYPTION_KEY if set, else derive one from
        JWT_SECRET (SHA-256 → urlsafe base64). Deterministic so restarts can still
        decrypt previously stored tokens."""
        if self.ENCRYPTION_KEY:
            return self.ENCRYPTION_KEY.encode()
        digest = hashlib.sha256(self.JWT_SECRET.encode()).digest()
        return base64.urlsafe_b64encode(digest)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """Async SQLAlchemy DSN (used from Phase 1 onward)."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis DSN used as the Celery broker/result backend (Phase 4)."""
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide singleton of parsed settings."""
    return Settings()
