"""Play router — engine replies for live games on the /play page.

Endpoints
---------
POST /api/play/move  — given a FEN and a difficulty, return Stockfish's reply.

Stateless by design: the client owns the game, the server only answers
positions. That keeps a refresh from stranding server-side game state, and means
no schema changes are needed to support live play.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.engine import DIFFICULTY_PROFILES, get_engine_move

router = APIRouter()
logger = logging.getLogger(__name__)


class EngineMoveRequest(BaseModel):
    fen: str
    difficulty: str = Field(
        default="intermediate",
        description="beginner | intermediate | advanced | maximum",
    )


class EngineMoveResponse(BaseModel):
    move_uci: str
    move_san: str
    eval_cp: float
    is_game_over: bool
    difficulty: str


@router.get("/difficulties")
async def list_difficulties():
    """Expose the available difficulty tiers and their engine settings."""
    return {
        "difficulties": [
            {
                "key": key,
                "skill_level": profile.skill_level,
                "depth": profile.depth,
            }
            for key, profile in DIFFICULTY_PROFILES.items()
        ]
    }


@router.post("/move", response_model=EngineMoveResponse)
async def engine_move(request: EngineMoveRequest):
    """Return the engine's reply to the given position."""
    try:
        result = await get_engine_move(
            fen=request.fen,
            difficulty=request.difficulty,
            stockfish_path=settings.stockfish_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError:
        logger.error("Stockfish binary not found at %s", settings.stockfish_path)
        raise HTTPException(
            status_code=503,
            detail="Engine unavailable — Stockfish is not installed on the server.",
        )
    except Exception as exc:
        logger.exception("Engine move failed: %s", exc)
        raise HTTPException(status_code=500, detail="Engine failed to produce a move.")

    return EngineMoveResponse(
        move_uci=result.move_uci,
        move_san=result.move_san,
        eval_cp=result.eval_cp,
        is_game_over=result.is_game_over,
        difficulty=result.difficulty,
    )
