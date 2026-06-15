"""Temporary auth helpers — provides a dev user until real auth is implemented.

In production this will be replaced with JWT/session-based authentication.
For now, all requests are attributed to a single dev user that is auto-created.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

# Fixed dev user ID — consistent across restarts
DEV_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEV_USERNAME = "dev_user"
DEV_EMAIL = "dev@chessian.ai"


async def ensure_dev_user(db: AsyncSession) -> uuid.UUID:
    """Ensure the dev user exists in the database. Returns user ID.

    Uses the caller's session to avoid double-session conflicts
    with FastAPI's dependency injection.
    """
    stmt = select(User).where(User.id == DEV_USER_ID)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            id=DEV_USER_ID,
            username=DEV_USERNAME,
            email=DEV_EMAIL,
            hashed_password="dev-no-password",
        )
        db.add(user)
        await db.flush()

    return DEV_USER_ID
