"""Auth endpoints: GitHub OAuth login/callback, current user, logout."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models import User
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.github import GitHubOAuthError
from app.modules.auth.service import (
    AuthService,
    InvalidOAuthStateError,
    OAuthNotConfiguredError,
)
from app.schemas.auth import LoginUrlResponse, UserOut

settings = get_settings()
router = APIRouter()


def _set_auth_cookie(response: Response, token: str) -> None:
    """Store our JWT in an httpOnly cookie so JS (and thus XSS) can't read it."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


@router.get("/github/login", response_model=LoginUrlResponse, summary="Start GitHub login")
async def github_login(db: AsyncSession = Depends(get_db)) -> LoginUrlResponse:
    """Return the GitHub authorize URL for the SPA to redirect to."""
    try:
        url = AuthService(db).build_login_url()
    except OAuthNotConfiguredError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and "
                "GITHUB_CLIENT_SECRET in your .env."
            ),
        ) from None
    return LoginUrlResponse(authorize_url=url)


@router.get("/github/callback", summary="GitHub OAuth callback")
async def github_callback(
    code: str, state: str, db: AsyncSession = Depends(get_db)
) -> RedirectResponse:
    """GitHub redirects here with `code` + `state`; we finish login and set the cookie."""
    service = AuthService(db)
    try:
        _user, token = await service.complete_login(code, state)
    except InvalidOAuthStateError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        ) from None
    except GitHubOAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub OAuth failed: {exc}",
        ) from exc

    response = RedirectResponse(url=settings.FRONTEND_URL, status_code=status.HTTP_302_FOUND)
    _set_auth_cookie(response, token)
    return response


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/logout", summary="Clear the session cookie")
async def logout() -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(settings.COOKIE_NAME, path="/")
    return response
