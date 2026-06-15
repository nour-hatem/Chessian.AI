"""Temporary auth helpers — provides a dev user until real auth is implemented.

In production this will be replaced with JWT/session-based authentication.
For now, all requests are attributed to a single dev user that is auto-created.
"""

import uuid

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User

# Fixed dev user ID — consistent across restarts
DEV_USER_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")
DEV_USERNAME = "dev_user"
DEV_EMAIL = "dev@chessian.ai"


async def ensure_dev_user(db: AsyncSession) -> uuid.UUID:
    """Ensure the dev user exists in the database. Returns user ID."""
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


async def get_current_user_id(
    db: AsyncSession = Depends(get_db),
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> uuid.UUID:
    """
    Get the current user's ID.

    For development: auto-creates and returns a dev user.
    Accepts optional X-User-ID header to support multi-user testing.
    """
    # In dev mode, always use/create the dev user
    return await ensure_dev_user(db)
