"""Top-level API router.

Every feature module exposes its own `APIRouter`; this file is the single place
that stitches them together under the versioned prefix (`/api/v1`). Adding a new
feature = write its router, then `include_router` it here. Versioning via prefix
lets us ship a `/api/v2` later without breaking existing clients.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import health
from app.modules.auth import router as auth
from app.modules.github import router as github

api_router = APIRouter()

# --- Phase 0 ---
api_router.include_router(health.router, tags=["health"])

# --- Phase 2 ---
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# --- Phase 3 ---
api_router.include_router(github.router, prefix="/repos", tags=["repositories"])

# --- Later phases plug in here ---
# api_router.include_router(search.router, prefix="/search", tags=["search"])    # P5
# api_router.include_router(reviews.router, prefix="/reviews", tags=["reviews"]) # P6
