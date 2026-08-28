"""Live-play engine service — single best-move lookups for the /play page.

Distinct from ``analyzer.py``, which evaluates a whole game offline. This module
answers one position at a time and is shaped for interactive latency, so it uses
shallower depths and Stockfish's own ``Skill Level`` option to produce genuinely
weaker play rather than perfect play that is merely slower.

It deliberately shares ``analyzer``'s semaphore: only one Stockfish process may
exist on this machine at a time, and a live game must not be able to start a
second engine while a background game analysis is running.
"""

import asyncio
import logging
from dataclasses import dataclass

import chess
import chess.engine

from app.services.analyzer import _engine_semaphore, _score_to_cp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DifficultyProfile:
    """Engine settings for one difficulty tier."""
    skill_level: int      # Stockfish "Skill Level" UCI option, 0-20
    depth: int
    movetime_ms: int      # hard cap so the UI never hangs on a slow position


# Approximate strengths. Skill Level is what actually weakens the engine;
# depth alone produces a strong engine that just thinks less.
DIFFICULTY_PROFILES: dict[str, DifficultyProfile] = {
    "beginner":     DifficultyProfile(skill_level=1,  depth=4,  movetime_ms=200),
    "intermediate": DifficultyProfile(skill_level=8,  depth=8,  movetime_ms=500),
    "advanced":     DifficultyProfile(skill_level=14, depth=14, movetime_ms=1000),
    "maximum":      DifficultyProfile(skill_level=20, depth=18, movetime_ms=2000),
}

DEFAULT_DIFFICULTY = "intermediate"


@dataclass
class EngineMove:
    """A single engine reply."""
    move_uci: str
    move_san: str
    eval_cp: float          # centipawns, positive = white is better
    is_game_over: bool
    difficulty: str


async def get_engine_move(
    fen: str,
    difficulty: str = DEFAULT_DIFFICULTY,
    stockfish_path: str = "/usr/bin/stockfish",
) -> EngineMove:
    """
    Return Stockfish's reply for ``fen`` at the given difficulty.

    Raises
    ------
    ValueError
        If the FEN is unparseable, or the position has no legal moves.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        raise ValueError(f"Invalid FEN: {exc}") from exc

    if board.is_game_over():
        raise ValueError("Position is already terminal — no move to make")

    profile = DIFFICULTY_PROFILES.get(
        (difficulty or "").lower(), DIFFICULTY_PROFILES[DEFAULT_DIFFICULTY]
    )

    async with _engine_semaphore:
        transport, engine = await chess.engine.popen_uci(stockfish_path)
        try:
            # Threads/Hash kept modest: this runs alongside the API event loop
            # and is called once per user move, not in a batch.
            await engine.configure(
                {
                    "Threads": 2,
                    "Hash": 128,
                    "Skill Level": profile.skill_level,
                }
            )

            limit = chess.engine.Limit(
                depth=profile.depth,
                time=profile.movetime_ms / 1000,
            )
            info = await engine.analyse(board, limit)

            pv = info.get("pv", [])
            if not pv:
                raise ValueError("Engine returned no principal variation")

            best = pv[0]
            move_san = board.san(best)
            move_uci = best.uci()
            eval_cp = _score_to_cp(info["score"])

            board.push(best)
            return EngineMove(
                move_uci=move_uci,
                move_san=move_san,
                eval_cp=eval_cp,
                is_game_over=board.is_game_over(),
                difficulty=profile_name(profile),
            )
        finally:
            try:
                await engine.quit()
            except Exception:
                pass
            finally:
                transport.close()


def profile_name(profile: DifficultyProfile) -> str:
    """Reverse-lookup the tier name for a profile (for echoing back to the UI)."""
    for name, p in DIFFICULTY_PROFILES.items():
        if p is profile:
            return name
    return DEFAULT_DIFFICULTY
