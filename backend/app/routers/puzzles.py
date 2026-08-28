"""Puzzles router — SM-2 spaced-repetition puzzle recommendation.

Endpoints
---------
GET  /api/puzzles/next               — next due puzzle (review first, else new)
POST /api/puzzles/{puzzle_id}/attempt — submit attempt result, advance SM-2
GET  /api/puzzles/stats              — aggregate stats + streak

Auth: ensure_dev_user() — same single hardcoded dev user as all other routers.
"""

import uuid
import logging
from datetime import datetime, timezone, date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc

from app.database import get_db
from app.models import Puzzle, PuzzleAttempt
from app.services.auth import ensure_dev_user
from app.services.sm2 import SM2State, update_sm2

router = APIRouter()
logger = logging.getLogger(__name__)

# Rating band configuration
# New users start at the lowest band center and the band widens as they
# attempt more puzzles.  After MIN_ATTEMPTS_FOR_ADAPTIVE_BAND correct
# solves the center shifts to their rolling average rating.
DEFAULT_RATING_CENTER = 900   # center of 800–1000, the lowest seeded band
RATING_BAND_HALF_WIDTH = 200
MIN_ATTEMPTS_FOR_ADAPTIVE_BAND = 10


# Helpers

async def _rating_center(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Return the rating center to use for puzzle selection for this user."""
    result = await db.execute(
        select(
            sqlfunc.count(PuzzleAttempt.id).label("n"),
            sqlfunc.avg(Puzzle.rating).label("avg"),
        )
        .join(Puzzle, PuzzleAttempt.puzzle_id == Puzzle.id)
        .where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.total_correct > 0,
        )
    )
    row = result.first()
    if row and row.n >= MIN_ATTEMPTS_FOR_ADAPTIVE_BAND and row.avg:
        return int(row.avg)
    return DEFAULT_RATING_CENTER


def _puzzle_payload(puzzle: Puzzle, attempt: PuzzleAttempt | None, is_new: bool) -> dict:
    """Serialise a puzzle + optional SM-2 state into the standard response dict."""
    sm2_data = None
    if attempt is not None:
        sm2_data = {
            "easiness": attempt.easiness,
            "interval": attempt.interval,
            "repetitions": attempt.repetitions,
            "next_due_date": attempt.next_due_date.isoformat() if attempt.next_due_date else None,
        }
    return {
        "puzzle_id": str(puzzle.id),
        "lichess_id": puzzle.lichess_id,
        "fen": puzzle.fen,
        "moves": puzzle.moves,
        "themes": puzzle.themes or [],
        "opening_tags": puzzle.opening_tags or [],
        "rating": puzzle.rating,
        "is_new": is_new,
        "sm2": sm2_data,
    }


# GET /next

@router.get("/next")
async def get_next_puzzle(db: AsyncSession = Depends(get_db)):
    """
    Return the next puzzle the user should solve.

    Selection priority:
      1. Overdue SM-2 review — PuzzleAttempt.next_due_date <= now, oldest first.
      2. New puzzle — not yet attempted, in user's current rating band,
         ordered ascending by rating (start easy within the band).
    """
    user_id = await ensure_dev_user(db)
    now = datetime.now(timezone.utc)

    # Priority 1: overdue review
    overdue = await db.execute(
        select(PuzzleAttempt, Puzzle)
        .join(Puzzle, PuzzleAttempt.puzzle_id == Puzzle.id)
        .where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.next_due_date <= now,
        )
        .order_by(PuzzleAttempt.next_due_date.asc())
        .limit(1)
    )
    row = overdue.first()
    if row:
        attempt, puzzle = row
        return _puzzle_payload(puzzle, attempt, is_new=False)

    # Priority 2: new puzzle in rating band
    center = await _rating_center(db, user_id)
    lo = max(0, center - RATING_BAND_HALF_WIDTH)
    hi = center + RATING_BAND_HALF_WIDTH

    # Exclude puzzles the user has already attempted
    seen_subq = select(PuzzleAttempt.puzzle_id).where(
        PuzzleAttempt.user_id == user_id
    )

    new_puzzle = await db.execute(
        select(Puzzle)
        .where(
            Puzzle.rating >= lo,
            Puzzle.rating <= hi,
            Puzzle.id.not_in(seen_subq),
        )
        .order_by(Puzzle.rating.asc())
        .limit(1)
    )
    puzzle = new_puzzle.scalar_one_or_none()

    if puzzle is None:
        raise HTTPException(
            status_code=404,
            detail="No puzzles available in your rating band. All reviewed or band has no coverage.",
        )

    return _puzzle_payload(puzzle, attempt=None, is_new=True)


# POST /{puzzle_id}/attempt

class AttemptRequest(BaseModel):
    correct: bool
    time_spent_ms: int = 0


@router.post("/{puzzle_id}/attempt")
async def submit_attempt(
    puzzle_id: uuid.UUID,
    body: AttemptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Record an attempt result and advance the SM-2 schedule for this puzzle.

    Quality mapping:
        wrong   → 0 (blackout: repetitions reset, interval reset to 1)
        correct → 3 (correct with effort: standard advancement)

    'Fast correct' (quality=5) is reserved for future UI enhancement.
    """
    user_id = await ensure_dev_user(db)

    # Verify puzzle exists
    puzzle = await db.execute(
        select(Puzzle).where(Puzzle.id == puzzle_id)
    )
    puzzle = puzzle.scalar_one_or_none()
    if puzzle is None:
        raise HTTPException(status_code=404, detail="Puzzle not found")

    # Fetch existing SM-2 state (or start fresh)
    existing = await db.execute(
        select(PuzzleAttempt).where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.puzzle_id == puzzle_id,
        )
    )
    attempt = existing.scalar_one_or_none()

    quality = 3 if body.correct else 0
    now = datetime.now(timezone.utc)

    if attempt is None:
        # First attempt on this puzzle — create a fresh SM-2 record
        current_state = SM2State()
        new_state, next_due = update_sm2(current_state, quality, today=now.date())
        attempt = PuzzleAttempt(
            user_id=user_id,
            puzzle_id=puzzle_id,
            easiness=new_state.easiness,
            interval=new_state.interval,
            repetitions=new_state.repetitions,
            next_due_date=datetime(
                next_due.year, next_due.month, next_due.day, tzinfo=timezone.utc
            ),
            last_attempted_at=now,
            last_quality=quality,
            total_attempts=1,
            total_correct=1 if body.correct else 0,
        )
        db.add(attempt)
    else:
        # Update existing SM-2 state
        current_state = SM2State(
            easiness=attempt.easiness,
            interval=attempt.interval,
            repetitions=attempt.repetitions,
        )
        new_state, next_due = update_sm2(current_state, quality, today=now.date())
        attempt.easiness = new_state.easiness
        attempt.interval = new_state.interval
        attempt.repetitions = new_state.repetitions
        attempt.next_due_date = datetime(
            next_due.year, next_due.month, next_due.day, tzinfo=timezone.utc
        )
        attempt.last_attempted_at = now
        attempt.last_quality = quality
        attempt.total_attempts += 1
        if body.correct:
            attempt.total_correct += 1

    await db.commit()
    await db.refresh(attempt)

    return {
        "puzzle_id": str(puzzle_id),
        "correct": body.correct,
        "quality": quality,
        "sm2": {
            "easiness": attempt.easiness,
            "interval": attempt.interval,
            "repetitions": attempt.repetitions,
            "next_due_date": attempt.next_due_date.isoformat(),
        },
        "total_attempts": attempt.total_attempts,
        "total_correct": attempt.total_correct,
    }


# GET /stats

@router.get("/stats")
async def get_puzzle_stats(db: AsyncSession = Depends(get_db)):
    """
    Return aggregate puzzle statistics for the current user.

    current_streak: consecutive correct answers counting backwards from the
    most recently attempted puzzle. Resets to 0 if the most recent was wrong.
    """
    user_id = await ensure_dev_user(db)
    now = datetime.now(timezone.utc)

    # Totals
    totals = await db.execute(
        select(
            sqlfunc.count(PuzzleAttempt.id).label("total_attempted"),
            sqlfunc.sum(PuzzleAttempt.total_correct).label("total_correct"),
        ).where(PuzzleAttempt.user_id == user_id)
    )
    t = totals.first()
    total_attempted = t.total_attempted or 0
    total_correct = int(t.total_correct or 0)

    # Puzzles due today (next_due_date <= now)
    due_result = await db.execute(
        select(sqlfunc.count(PuzzleAttempt.id))
        .where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.next_due_date <= now,
        )
    )
    puzzles_due_today = due_result.scalar_one() or 0

    # Solved today: attempts last answered correctly during the current UTC day.
    solved_today_result = await db.execute(
        select(sqlfunc.count(PuzzleAttempt.id))
        .where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.last_attempted_at.is_not(None),
            sqlfunc.date(PuzzleAttempt.last_attempted_at) == now.date(),
            PuzzleAttempt.last_quality >= 3,
        )
    )
    solved_today = solved_today_result.scalar_one() or 0

    # Current streak: walk attempts by last_attempted_at DESC,
    # count consecutive last_quality >= 3 from the top.
    recent = await db.execute(
        select(PuzzleAttempt.last_quality)
        .where(
            PuzzleAttempt.user_id == user_id,
            PuzzleAttempt.last_attempted_at.is_not(None),
        )
        .order_by(PuzzleAttempt.last_attempted_at.desc())
        .limit(100)  # cap — a streak > 100 would be remarkable
    )
    streak = 0
    for (q,) in recent:
        if q is not None and q >= 3:
            streak += 1
        else:
            break

    rating_center = await _rating_center(db, user_id)

    return {
        "total_attempted": total_attempted,
        "total_correct": total_correct,
        "current_streak": streak,
        "puzzles_due_today": puzzles_due_today,
        "solved_today": solved_today,
        "rating_center": rating_center,
    }
