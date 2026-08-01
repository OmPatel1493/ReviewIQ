"""Shallow-clone a GitHub repository to a local temp directory.

We use `git clone --depth 1` (only the latest commit, one branch) because indexing
needs the current file tree, not the history — that's dramatically faster and smaller.
For private repos we inject the user's OAuth token into the clone URL; the clone lives
in an ephemeral temp dir that the caller deletes right after indexing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from urllib.parse import urlparse, urlunparse


class CloneError(Exception):
    """git clone failed (bad URL, auth, network, timeout)."""


def build_authenticated_url(clone_url: str, token: str | None) -> str:
    """Embed the token for HTTPS clones; return the URL unchanged otherwise."""
    if not token:
        return clone_url
    parsed = urlparse(clone_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return clone_url
    netloc = f"x-access-token:{token}@{parsed.hostname}"
    if parsed.port:
        netloc += f":{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))


def clone_repository(
    clone_url: str, token: str | None, dest: Path, *, ref: str | None = None
) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    url = build_authenticated_url(clone_url, token)

    cmd = ["git", "clone", "--depth", "1", "--single-branch"]
    if ref:
        cmd += ["--branch", ref]
    cmd += [url, str(dest)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        raise CloneError("git clone timed out after 300s") from exc

    if result.returncode != 0:
        # Never let the token leak into an error message/log.
        stderr = result.stderr
        if token:
            stderr = stderr.replace(token, "***")
        raise CloneError(f"git clone failed: {stderr.strip()[:500]}")
    return dest
