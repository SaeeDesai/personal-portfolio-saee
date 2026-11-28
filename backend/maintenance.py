from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from backend.database import SessionLocal
from backend.models import AnalyticsEvent, AdminSession, LoginAttempt
from threading import Lock
from time import monotonic

RETENTION_DAYS = 90


def cleanup():
    now = datetime.now(timezone.utc)

    with SessionLocal.begin() as db:
        events = db.execute(
            delete(AnalyticsEvent).where(
                AnalyticsEvent.created_at <
                now - timedelta(days=RETENTION_DAYS)
            )
        )

        sessions = db.execute(
            delete(AdminSession).where(
                AdminSession.expires_at <= now
            )
        )

        attempts = db.execute(
            delete(LoginAttempt).where(
                LoginAttempt.created_at <
                now - timedelta(minutes=15)
            )
        )

        print(f"Expired analytics events removed: {events.rowcount}")
        print(f"Expired admin sessions removed: {sessions.rowcount}")
        print(f"Old login attempts removed: {attempts.rowcount}")

CLEANUP_INTERVAL = 86400  # 24 hours

cleanup_lock = Lock()
last_cleanup = None


def maybe_cleanup():
    global last_cleanup

    now = monotonic()

    with cleanup_lock:
        if (
            last_cleanup is not None
            and now - last_cleanup < CLEANUP_INTERVAL
        ):
            return

        cleanup()
        last_cleanup = monotonic()

if __name__ == "__main__":
    cleanup()