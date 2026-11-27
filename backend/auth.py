import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AdminSession, LoginAttempt
from sqlalchemy import delete, select, func, text


COOKIE_NAME = "pp_admin_session"
SESSION_DURATION = timedelta(hours=8)

password_hasher = PasswordHasher()


def verify_credentials(username: str, password: str) -> bool:
    expected_username = os.environ["ADMIN_USERNAME"]
    expected_hash = os.environ["ADMIN_PASSWORD_HASH"]

    try:
        password_valid = password_hasher.verify(
            expected_hash, password
        )
    except (VerificationError, InvalidHashError):
        password_valid = False

    username_valid = secrets.compare_digest(
        username.encode("utf-8"),
        expected_username.encode("utf-8"),
    )

    return username_valid and password_valid


def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_admin_session(db: Session) -> str:
    db.execute(
        delete(AdminSession).where(
            AdminSession.expires_at <= datetime.now(timezone.utc)
        )
    )

    token = secrets.token_urlsafe(32)

    session = AdminSession(
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + SESSION_DURATION,
    )

    db.add(session)
    db.commit()

    return token


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    session = db.get(AdminSession, hash_token(token))

    if (
        session is None
        or session.expires_at <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session",
        )

    return session


def revoke_admin_session(db: Session, token: str):
    session = db.get(AdminSession, hash_token(token))

    if session is not None:
        db.delete(session)
        db.commit()

MAX_LOGIN_ATTEMPTS = 5
LOGIN_WINDOW_SECONDS = 900


def enforce_login_rate_limit(
    db: Session = Depends(get_db),
):
    # Serialize login attempts across backend workers.
    db.execute(
        text("SELECT pg_advisory_xact_lock(712301)")
    )

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=LOGIN_WINDOW_SECONDS)

    db.execute(
        delete(LoginAttempt).where(
            LoginAttempt.created_at <= cutoff
        )
    )

    attempts = db.scalar(
        select(func.count()).select_from(LoginAttempt)
    )

    if attempts >= MAX_LOGIN_ATTEMPTS:
        db.rollback()

        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )

    db.add(LoginAttempt(created_at=now))
    db.commit()

def verify_auth_origin(request: Request):
    expected_origin = os.getenv(
        "DASHBOARD_ORIGIN",
        "http://localhost:8001",
    )

    if request.headers.get("origin") != expected_origin:
        raise HTTPException(
            status_code=403,
            detail="Untrusted request origin",
        )