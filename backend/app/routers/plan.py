"""Improvement Plan router (D1) — generates personalized training curricula."""

import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ImprovementPlanResponse
from app.services.auth import ensure_dev_user
from app.services.curriculum import build_improvement_plan, toggle_task_completed

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=ImprovementPlanResponse)
async def get_improvement_plan(
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the personalized improvement plan for the active user.

    Computes performance metrics across all analyzed games, isolates the weakest
    phase, scores tactical weaknesses, and returns structured weekly tasks.
    """
    user_id = await ensure_dev_user(db)
    try:
        plan = await build_improvement_plan(db, user_id)
        return plan
    except Exception as e:
        logger.exception("Failed to build improvement plan: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate improvement plan")


@router.post("/tasks/{task_id}/toggle")
async def toggle_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Toggle a task's completed state."""
    user_id = await ensure_dev_user(db)
    is_completed = toggle_task_completed(user_id, task_id)
    return {"task_id": task_id, "completed": is_completed}
