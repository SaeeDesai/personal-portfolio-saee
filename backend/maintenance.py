from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from backend.database import SessionLocal
from backend.models import AnalyticsEvent, AdminSession, LoginAttempt


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


if __name__ == "__main__":
    cleanup()