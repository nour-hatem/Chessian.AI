"""Curriculum & Improvement Plan service (D1).

Generates a structured, data-driven improvement plan based on the player's
historical games, phase-separated accuracy, opening repertoire, and puzzle
progress. Prioritizes weaknesses by expected rating gain and generates an
LLM coaching synthesis.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, case, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Game, GameAnalysis, PuzzleAttempt, Puzzle
from app.schemas import (
    ImprovementPlanResponse,
    WeaknessItem,
    PlanTask,
)
from app.services import crud
from app.services.explainer import _call_groq

logger = logging.getLogger(__name__)

# In-memory store for task completion state per user across session
_completed_tasks_store: dict[str, set[str]] = {}


def is_task_completed(user_id: uuid.UUID, task_id: str) -> bool:
    """Check if a task is marked complete for this user."""
    return task_id in _completed_tasks_store.get(str(user_id), set())


def toggle_task_completed(user_id: uuid.UUID, task_id: str) -> bool:
    """Toggle a task's completed status and return the new state."""
    uid = str(user_id)
    if uid not in _completed_tasks_store:
        _completed_tasks_store[uid] = set()
    completed_set = _completed_tasks_store[uid]
    if task_id in completed_set:
        completed_set.remove(task_id)
        return False
    else:
        completed_set.add(task_id)
        return True


async def generate_coaching_summary(
    username: str,
    total_games: int,
    overall_acc: float,
    opening_acc: float,
    middlegame_acc: float,
    endgame_acc: float,
    weakest_phase: str,
    blunder_rate: float,
    mistake_rate: float,
    trouble_opening: Optional[str],
) -> tuple[str, str]:
    """Generate an AI coaching diagnostic using Groq LLM with a reliable fallback."""
    headline = f"{weakest_phase.capitalize()} Stability & Tactical Vigilance"

    fallback_summary = (
        f"Across your {total_games} analyzed games, your primary performance bottleneck "
        f"is in the {weakest_phase.lower()} (averaging {weakest_acc_lookup(weakest_phase, opening_acc, middlegame_acc, endgame_acc):.1f}% accuracy), "
        f"compounded by an average of {blunder_rate:.1f} blunders per game. "
        + (f"In particular, your results in the {trouble_opening} indicate theoretical vulnerabilities. " if trouble_opening else "")
        + "This week, focus on tactical discipline before every move and deliberate practice to solidify your transitional play."
    )

    if not settings.groq_api_key:
        return headline, fallback_summary

    system_prompt = (
        "You are an elite, encouraging chess coach. "
        "Review the player's diagnostic metrics and produce a 2-3 sentence personalized weekly coaching diagnosis. "
        "Highlight their biggest performance leak and give clear, direct advice on what to focus on. "
        "Do not use markdown headers or bullet points. Speak directly to the player ('you', 'your')."
    )

    user_prompt = (
        f"Player: {username}\n"
        f"Games Analyzed: {total_games}\n"
        f"Overall Accuracy: {overall_acc:.1f}%\n"
        f"Opening Accuracy: {opening_acc:.1f}%\n"
        f"Middlegame Accuracy: {middlegame_acc:.1f}%\n"
        f"Endgame Accuracy: {endgame_acc:.1f}%\n"
        f"Weakest Phase: {weakest_phase}\n"
        f"Blunders Per Game: {blunder_rate:.1f}\n"
        f"Mistakes Per Game: {mistake_rate:.1f}\n"
        + (f"Trouble Opening Line: {trouble_opening}\n" if trouble_opening else "")
        + "Give a concise 2-3 sentence coaching briefing for this week's improvement plan."
    )

    try:
        # Run Groq with a 3-second timeout
        res = await asyncio.wait_for(
            asyncio.to_thread(_call_groq, settings.groq_api_key, system_prompt, user_prompt),
            timeout=3.5,
        )
        if res and len(res.strip()) > 30:
            return headline, res.strip()
    except Exception as e:
        logger.warning("Groq plan summary generation unavailable: %s", e)

    return headline, fallback_summary


def weakest_acc_lookup(phase: str, op: float, mid: float, end: float) -> float:
    p = phase.lower()
    if p == "opening":
        return op
    elif p == "middlegame":
        return mid
    return end


async def build_improvement_plan(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> ImprovementPlanResponse:
    """Build the complete D1 Improvement Plan for a user."""
    usernames = await crud.resolve_user_usernames(db, user_id)
    user_lower = usernames[0] if usernames else None

    # 1. Query game analysis aggregates for the user
    user_acc_expr = case(
        (func.lower(Game.white_username) == user_lower, GameAnalysis.white_accuracy),
        (func.lower(Game.black_username) == user_lower, GameAnalysis.black_accuracy),
        else_=(GameAnalysis.white_accuracy + GameAnalysis.black_accuracy) / 2.0,
    )
    user_blunders_expr = case(
        (func.lower(Game.white_username) == user_lower, GameAnalysis.white_blunders),
        (func.lower(Game.black_username) == user_lower, GameAnalysis.black_blunders),
        else_=(GameAnalysis.white_blunders + GameAnalysis.black_blunders) / 2.0,
    )
    user_mistakes_expr = case(
        (func.lower(Game.white_username) == user_lower, GameAnalysis.white_mistakes),
        (func.lower(Game.black_username) == user_lower, GameAnalysis.black_mistakes),
        else_=(GameAnalysis.white_mistakes + GameAnalysis.black_mistakes) / 2.0,
    )

    game_filter = (
        or_(
            func.lower(Game.white_username) == user_lower,
            func.lower(Game.black_username) == user_lower,
        )
        if user_lower
        else True
    )

    stats_stmt = (
        select(
            func.count(Game.id).label("total_games"),
            func.avg(user_acc_expr).label("avg_user_acc"),
            func.avg(GameAnalysis.opening_accuracy).label("avg_opening_acc"),
            func.avg(GameAnalysis.middlegame_accuracy).label("avg_middlegame_acc"),
            func.avg(GameAnalysis.endgame_accuracy).label("avg_endgame_acc"),
            func.avg(user_blunders_expr).label("avg_blunders"),
            func.avg(user_mistakes_expr).label("avg_mistakes"),
        )
        .join(GameAnalysis, Game.id == GameAnalysis.game_id)
        .where(
            Game.user_id == user_id,
            GameAnalysis.status == "complete",
            game_filter,
        )
    )
    row = (await db.execute(stats_stmt)).first()

    total_games = row.total_games if row and row.total_games else 0
    overall_acc = round(float(row.avg_user_acc or 0.0), 1) if row else 0.0
    opening_acc = round(float(row.avg_opening_acc or 0.0), 1) if row else 0.0
    middlegame_acc = round(float(row.avg_middlegame_acc or 0.0), 1) if row else 0.0
    endgame_acc = round(float(row.avg_endgame_acc or 0.0), 1) if row else 0.0
    blunder_rate = round(float(row.avg_blunders or 0.0), 1) if row else 0.0
    mistake_rate = round(float(row.avg_mistakes or 0.0), 1) if row else 0.0

    # Determine weakest phase
    phase_scores = [
        ("Middlegame", middlegame_acc),
        ("Opening", opening_acc),
        ("Endgame", endgame_acc),
    ]
    # Filter out 0.0 if incomplete, otherwise pick lowest
    valid_phases = [p for p in phase_scores if p[1] > 0]
    if valid_phases:
        weakest_phase = min(valid_phases, key=lambda x: x[1])[0]
    else:
        weakest_phase = "Middlegame"

    # 2. Query opening repertoire for problem lines
    openings = await crud.get_opening_repertoire(db, user_id, usernames, min_games=2)
    trouble_opening = None
    trouble_opening_data = None
    if openings:
        # Find opening with score < 50% or lowest score
        sorted_openings = sorted(
            openings,
            key=lambda o: (o["score_pct"] if o["score_pct"] is not None else 50.0, o["games_played"]),
        )
        trouble_opening_data = sorted_openings[0]
        trouble_opening = f"{trouble_opening_data['eco']} {trouble_opening_data['name']}"

    # 3. Query puzzle & SM-2 stats
    puz_stmt = select(
        func.count(PuzzleAttempt.id).label("total_attempted"),
        func.sum(case((PuzzleAttempt.total_correct > 0, 1), else_=0)).label("total_correct"),
        func.avg(Puzzle.rating).label("avg_rating"),
    ).join(Puzzle, PuzzleAttempt.puzzle_id == Puzzle.id).where(PuzzleAttempt.user_id == user_id)
    puz_row = (await db.execute(puz_stmt)).first()

    puzzle_rating_center = int(round(float(puz_row.avg_rating or 800))) if puz_row and puz_row.avg_rating else 800

    now = datetime.now(timezone.utc)
    due_stmt = select(func.count(PuzzleAttempt.id)).where(
        PuzzleAttempt.user_id == user_id,
        PuzzleAttempt.next_due_date <= now,
    )
    puzzles_due_count = (await db.execute(due_stmt)).scalar() or 0

    # 4. Synthesize Prioritized Weaknesses (D1 Priority Scoring)
    weaknesses: list[WeaknessItem] = []

    # Weakness 1: Weakest Game Phase
    weaknesses.append(
        WeaknessItem(
            id="weakness_phase",
            title=f"{weakest_phase} Precision Drop",
            description=(
                f"Your accuracy in the {weakest_phase.lower()} is {weakest_acc_lookup(weakest_phase, opening_acc, middlegame_acc, endgame_acc):.1f}%, "
                f"which is your lowest performing phase across {total_games} games. Complex transitions lead to suboptimal piece placement."
            ),
            severity="high",
            expected_gain_elo=45,
            dimension=weakest_phase.lower(),
            metric=f"{weakest_phase} Acc: {weakest_acc_lookup(weakest_phase, opening_acc, middlegame_acc, endgame_acc):.1f}%",
        )
    )

    # Weakness 2: Tactical Blunder Rate
    if blunder_rate > 1.0:
        weaknesses.append(
            WeaknessItem(
                id="weakness_tactics",
                title="Tactical Oversights & Material Drops",
                description=(
                    f"You average {blunder_rate:.1f} blunders and {mistake_rate:.1f} mistakes per game. "
                    "Unforced tactical errors account for the majority of sudden evaluation collapses."
                ),
                severity="high" if blunder_rate >= 2.0 else "medium",
                expected_gain_elo=60,
                dimension="tactics",
                metric=f"{blunder_rate:.1f} blunders / game",
            )
        )

    # Weakness 3: Repertoire vulnerability
    if trouble_opening_data:
        score_pct = trouble_opening_data["score_pct"] or 0.0
        weaknesses.append(
            WeaknessItem(
                id="weakness_opening",
                title=f"Theoretical Underperformance: {trouble_opening_data['name']}",
                description=(
                    f"In {trouble_opening_data['name']} ({trouble_opening_data['eco']}), your score rate is {score_pct:.0f}% "
                    f"across {trouble_opening_data['games_played']} games. Early inaccuracies give opponents easy initiative."
                ),
                severity="medium",
                expected_gain_elo=30,
                dimension="opening",
                metric=f"{score_pct:.0f}% win rate ({trouble_opening_data['games_played']} games)",
            )
        )

    # Weakness 4: Memory retention
    weaknesses.append(
        WeaknessItem(
            id="weakness_retention",
            title="Spaced Repetition Review Backlog",
            description=(
                f"You have {puzzles_due_count} tactical puzzles scheduled by the SM-2 spaced repetition algorithm "
                "that are due for review. Timely recall prevents tactical motif decay."
            ),
            severity="medium" if puzzles_due_count > 10 else "low",
            expected_gain_elo=25,
            dimension="tactics",
            metric=f"{puzzles_due_count} reviews due",
        )
    )

    # 5. Formulate Actionable Weekly Tasks
    tasks: list[PlanTask] = [
        PlanTask(
            id="task_puzzles_tactics",
            title=f"Solve 15 Adaptive Tactical Puzzles (Rating ~{puzzle_rating_center})",
            category="puzzles",
            duration_minutes=25,
            description="Complete 15 puzzles matched to your tactical rating band to build defensive scanning habits.",
            action_url="/puzzles",
            action_label="Solve Puzzles",
            completed=is_task_completed(user_id, "task_puzzles_tactics"),
        ),
        PlanTask(
            id="task_puzzles_reviews",
            title=f"Clear {min(puzzles_due_count, 20)} Due Spaced-Repetition Reviews",
            category="puzzles",
            duration_minutes=15,
            description="Review scheduled SM-2 tactical puzzles to reinforce long-term pattern recognition.",
            action_url="/puzzles",
            action_label="Review Queue",
            completed=is_task_completed(user_id, "task_puzzles_reviews"),
        ),
    ]

    if trouble_opening_data:
        tasks.append(
            PlanTask(
                id="task_opening_study",
                title=f"Repertoire Study: {trouble_opening_data['name']}",
                category="openings",
                duration_minutes=20,
                description=f"Inspect your historical games in {trouble_opening_data['name']} ({trouble_opening_data['eco']}) and compare with master continuations.",
                action_url="/openings",
                action_label="Study Opening",
                completed=is_task_completed(user_id, "task_opening_study"),
            )
        )

    tasks.append(
        PlanTask(
            id="task_phase_practice",
            title=f"{weakest_phase} Drill vs Stockfish Engine",
            category="play",
            duration_minutes=30,
            description=f"Play 2 training games against Stockfish (Medium difficulty) focusing specifically on calm piece coordination through the {weakest_phase.lower()}.",
            action_url="/play?difficulty=medium",
            action_label="Play Engine",
            completed=is_task_completed(user_id, "task_phase_practice"),
        )
    )

    tasks.append(
        PlanTask(
            id="task_blunder_audit",
            title="Blunder Post-Mortem: Review 3 Critical Moments",
            category="analysis",
            duration_minutes=20,
            description="Open your library, filter for your latest losses, and read the AI natural language explanations for your highest centipawn loss blunders.",
            action_url="/library",
            action_label="Review Games",
            completed=is_task_completed(user_id, "task_blunder_audit"),
        )
    )

    # 6. Generate Coaching Summary
    headline, coaching_summary = await generate_coaching_summary(
        username=user_lower or "Player",
        total_games=total_games,
        overall_acc=overall_acc,
        opening_acc=opening_acc,
        middlegame_acc=middlegame_acc,
        endgame_acc=endgame_acc,
        weakest_phase=weakest_phase,
        blunder_rate=blunder_rate,
        mistake_rate=mistake_rate,
        trouble_opening=trouble_opening,
    )

    total_minutes = sum(t.duration_minutes for t in tasks)
    planned_hours = round(total_minutes / 60.0, 1)

    return ImprovementPlanResponse(
        user_id=user_id,
        resolved_username=user_lower,
        total_games_analyzed=total_games,
        overall_accuracy=overall_acc,
        opening_accuracy=opening_acc,
        middlegame_accuracy=middlegame_acc,
        endgame_accuracy=endgame_acc,
        weakest_phase=weakest_phase,
        blunder_rate_per_game=blunder_rate,
        mistake_rate_per_game=mistake_rate,
        puzzle_rating_center=puzzle_rating_center,
        puzzles_due_count=puzzles_due_count,
        puzzle_streak=0,
        coaching_summary=coaching_summary,
        focus_headline=headline,
        planned_hours=planned_hours,
        weaknesses=weaknesses,
        tasks=tasks,
    )
