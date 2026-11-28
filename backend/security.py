import os
from collections import deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

MAX_EVENT_REQUESTS = 120
EVENT_WINDOW_SECONDS = 60

event_attempts = deque()
event_lock = Lock()


def enforce_event_rate_limit():
    now = monotonic()

    with event_lock:
        while (
            event_attempts
            and now - event_attempts[0] >= EVENT_WINDOW_SECONDS
        ):
            event_attempts.popleft()

        if len(event_attempts) >= MAX_EVENT_REQUESTS:
            raise HTTPException(
                status_code=429,
                detail="Analytics rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        event_attempts.append(now)


def verify_event_origin(request: Request):
    allowed_origins = {
        "https://saeedesai.github.io",
    }

    if os.getenv("APP_ENV") == "development":
        allowed_origins.update({
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        })

    if request.headers.get("origin") not in allowed_origins:
        raise HTTPException(
            status_code=403,
            detail="Untrusted event origin",
        )

class RequestSizeLimitMiddleware:
    def __init__(self, app, max_bytes=8192):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["path"] not in {"/events", "/auth/login"}
            or scope["method"] != "POST"
        ):
            await self.app(scope, receive, send)
            return

        body = bytearray()

        while True:
            message = await receive()

            if message["type"] == "http.disconnect":
                return

            chunk = message.get("body", b"")

            if len(body) + len(chunk) > self.max_bytes:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )
                await response(scope, receive, send)
                return

            body.extend(chunk)

            if not message.get("more_body", False):
                break

        delivered = False

        async def limited_receive():
            nonlocal delivered

            if not delivered:
                delivered = True
                return {
                    "type": "http.request",
                    "body": bytes(body),
                    "more_body": False,
                }

            return await receive()

        await self.app(scope, limited_receive, send)

from uuid import UUID

MAX_SESSION_EVENTS = 40

session_attempts = {}


def enforce_session_rate_limit(session_id: UUID):
    now = monotonic()

    with event_lock:
        for key, attempts in list(session_attempts.items()):
            while attempts and now - attempts[0] >= EVENT_WINDOW_SECONDS:
                attempts.popleft()

            if not attempts:
                del session_attempts[key]

        attempts = session_attempts.setdefault(
            session_id, deque()
        )

        if len(attempts) >= MAX_SESSION_EVENTS:
            raise HTTPException(
                status_code=429,
                detail="Session rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        attempts.append(now)