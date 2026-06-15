"""Temporary auth helpers — provides a dev user until real auth is implemented.

In production this will be replaced with JWT/session-based authentication.
For now, all requests are attributed to a single dev user that is auto-created.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

# Fixed dev user ID — consistent across restarts
DEV_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEV_USERNAME = "dev_user"
DEV_EMAIL = "dev@chessian.ai"


async def ensure_dev_user(db: AsyncSession) -> uuid.UUID:
    """Ensure the dev user exists in the database. Returns user ID.

    Uses an atomic INSERT ... ON CONFLICT DO NOTHING to avoid
    race conditions when multiple requests arrive simultaneously.
    """
    stmt = (
        pg_insert(User)
        .values(
            id=DEV_USER_ID,
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            hashed_password="dev-no-password",
        )
        .on_conflict_do_nothing(index_elements=["id"])
    )
    await db.execute(stmt)
    await db.flush()

    return DEV_USER_ID
