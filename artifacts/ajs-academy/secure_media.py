"""Role- and browser-session-bound media serving for AJ's Academy."""
from __future__ import annotations

import hashlib
import html
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from urllib.parse import quote

import streamlit as st
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

COOKIE_NAME = "academy_media_session"
MEDIA_PATH = "/academy-media"
SESSION_TTL_SECONDS = 1800
_RANGE = re.compile(r"bytes=(\d*)-(\d*)$")


@dataclass(frozen=True)
class SessionGrant:
    role: str
    expires_at: float


@dataclass(frozen=True)
class MediaRecord:
    content: bytes
    mime: str
    filename: str | None
    owner_nonce: str
    allowed_roles: frozenset[str]
    expires_at: float


_lock = threading.RLock()
_sessions: dict[str, SessionGrant] = {}
_media: dict[str, MediaRecord] = {}
_media_cache: dict[tuple[str, bytes, str, str | None, tuple[str, ...]], str] = {}


def new_session_nonce() -> str:
    """Create an unguessable browser-session binding, independent of media URLs."""
    return secrets.token_urlsafe(32)


def grant_session(nonce: str, role: str, expires_at: float) -> None:
    if role not in {"parent", "child"}:
        raise ValueError("Unknown Academy role.")
    with _lock:
        _prune(time.time())
        _sessions[nonce] = SessionGrant(role=role, expires_at=expires_at)


def revoke_session(nonce: str | None) -> None:
    if not nonce:
        return
    with _lock:
        _sessions.pop(nonce, None)
        for token, record in list(_media.items()):
            if record.owner_nonce == nonce:
                _media.pop(token, None)
        for key in list(_media_cache):
            if key[0] == nonce:
                _media_cache.pop(key, None)


def _prune(now: float) -> None:
    expired_nonces = {
        nonce for nonce, grant in _sessions.items() if grant.expires_at <= now
    }
    for nonce in expired_nonces:
        revoke_session(nonce)
    for token, record in list(_media.items()):
        if record.expires_at <= now:
            _media.pop(token, None)
    live_tokens = set(_media)
    for key, token in list(_media_cache.items()):
        if token not in live_tokens:
            _media_cache.pop(key, None)


def register(
    content: bytes,
    mime: str,
    filename: str | None,
    *,
    nonce: str,
    role: str,
    allowed_roles: tuple[str, ...],
) -> str:
    """Register bytes for this session and return an opaque, unguessable URL."""
    if role not in allowed_roles:
        raise PermissionError("This role cannot issue this media.")
    if not isinstance(content, bytes):
        content = bytes(content)
    allowed = tuple(sorted(set(allowed_roles)))
    digest = hashlib.sha256(content).digest()
    cache_key = (nonce, digest, mime, filename, allowed)
    now = time.time()
    with _lock:
        _prune(now)
        grant = _sessions.get(nonce)
        if not grant or grant.role != role or grant.expires_at <= now:
            raise PermissionError("The Academy session is no longer active.")
        existing = _media_cache.get(cache_key)
        if existing and existing in _media:
            current = _media[existing]
            _media[existing] = MediaRecord(
                content=current.content,
                mime=current.mime,
                filename=current.filename,
                owner_nonce=current.owner_nonce,
                allowed_roles=current.allowed_roles,
                expires_at=grant.expires_at,
            )
            return f"{MEDIA_PATH}/{existing}"
        token = secrets.token_urlsafe(32)
        _media[token] = MediaRecord(
            content=content,
            mime=mime,
            filename=filename,
            owner_nonce=nonce,
            allowed_roles=frozenset(allowed),
            expires_at=grant.expires_at,
        )
        _media_cache[cache_key] = token
    return f"{MEDIA_PATH}/{token}"


def _parse_range(value: str, size: int) -> tuple[int, int] | None:
    match = _RANGE.fullmatch(value.strip())
    if not match or size == 0:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    try:
        if not first:
            suffix_length = int(last)
            if suffix_length <= 0:
                return None
            return max(0, size - suffix_length), size - 1
        start = int(first)
        end = int(last) if last else size - 1
    except ValueError:
        return None
    if start >= size or end < start:
        return None
    return start, min(end, size - 1)


async def media_endpoint(request: Request) -> Response:
    """Serve a single private resource only to its issuing active browser session."""
    nonce = request.cookies.get(COOKIE_NAME)
    now = time.time()
    with _lock:
        _prune(now)
        grant = _sessions.get(nonce or "")
        record = _media.get(request.path_params["token"])
        if not grant or grant.expires_at <= now:
            status = 401
            record = None
        elif (
            not record
            or record.expires_at <= now
            or record.owner_nonce != nonce
            or grant.role not in record.allowed_roles
        ):
            status = 403
            record = None
        else:
            status = 200

    base_headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Accept-Ranges": "bytes",
        "Vary": "Cookie",
    }
    if status != 200 or record is None:
        return Response(status_code=status, headers=base_headers)

    content = record.content
    headers = {
        **base_headers,
        "Content-Type": record.mime,
        "Content-Length": str(len(content)),
    }
    if record.filename:
        headers["Content-Disposition"] = (
            "attachment; filename*=UTF-8''" + quote(record.filename, safe="")
        )
    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    range_header = request.headers.get("range")
    if range_header:
        byte_range = _parse_range(range_header, len(content))
        if byte_range is None:
            headers["Content-Range"] = f"bytes */{len(content)}"
            return Response(status_code=416, headers=headers)
        start, end = byte_range
        headers["Content-Range"] = f"bytes {start}-{end}/{len(content)}"
        headers["Content-Length"] = str(end - start + 1)
        return Response(
            content[start : end + 1],
            status_code=206,
            headers=headers,
            media_type=None,
        )
    return Response(content, status_code=200, headers=headers, media_type=None)


def routes() -> list[Route]:
    return [
        Route(
            f"{MEDIA_PATH}/{{token}}",
            media_endpoint,
            methods=["GET", "HEAD"],
        )
    ]


def _cookie_script(value: str | None) -> str:
    """Build a same-origin cookie update/removal for the app's iframe."""
    if value:
        cookie = (
            f"{COOKIE_NAME}={value}; Path=/; SameSite=Strict; "
            f"Max-Age={SESSION_TTL_SECONDS}"
        )
        script = (
            f"var c={json.dumps(cookie)};"
            "if(location.protocol==='https:')c+='; Secure';"
            "document.cookie=c;"
            "try{parent.document.cookie=c}catch(e){}"
        )
    else:
        cookie = f"{COOKIE_NAME}=; Path=/; Max-Age=0; SameSite=Strict"
        script = (
            f"var c={json.dumps(cookie)};"
            "document.cookie=c;"
            "try{parent.document.cookie=c}catch(e){}"
        )
    return f"<!doctype html><html><body><script>{script}</script></body></html>"


def sync_browser_session(nonce: str | None) -> None:
    """Keep the browser cookie aligned with the currently authorized session."""
    st.html(
        _cookie_script(nonce),
        width=1,
        unsafe_allow_javascript=True,
    )


def render(content: bytes, mime: str, alt: str, *, nonce: str, role: str) -> None:
    """Render a private attachment in an iframe using the protected route."""
    url = register(
        content,
        mime,
        None,
        nonce=nonce,
        role=role,
        allowed_roles=("parent", "child"),
    )
    safe_url = html.escape(url, quote=True)
    if mime.startswith("image/"):
        body = (
            f'<img src="{safe_url}" alt="{html.escape(alt, quote=True)}" '
            'style="display:block;width:auto;max-width:300px;max-height:420px;'
            'object-fit:contain;">'
        )
        width = 300
    elif mime.startswith("audio/"):
        body = f'<audio src="{safe_url}" controls style="width:100%;"></audio>'
        width = "stretch"
    elif mime.startswith("video/"):
        body = (
            f'<video src="{safe_url}" controls playsinline '
            'style="display:block;width:100%;max-width:640px;max-height:420px;">'
            "</video>"
        )
        width = 640
    else:
        return
    st.html(
        "<!doctype html><html><body style=\"margin:0\">"
        + body
        + "</body></html>",
        width=width,
    )


def download_link(
    label: str,
    content: bytes | str,
    filename: str,
    mime: str,
    *,
    nonce: str,
    role: str,
) -> None:
    """Render a parent-only download as a protected attachment link."""
    payload = content.encode("utf-8") if isinstance(content, str) else content
    url = register(
        payload,
        mime,
        filename,
        nonce=nonce,
        role=role,
        allowed_roles=("parent",),
    )
    st.link_button(label, url, use_container_width=True)
