"""Analysis router — triggers and retrieves game analyses."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/{game_id}")
async def trigger_analysis(game_id: str, depth: int = 20):
    """Trigger Stockfish analysis for a game."""
    # TODO: queue analysis job via Celery/ARQ
    return {
        "game_id": game_id,
        "status": "queued",
        "depth": depth,
        "message": "Analysis queued. Check status at GET /api/analysis/{game_id}",
    }


@router.get("/{game_id}")
async def get_analysis(game_id: str):
    """Get analysis results for a game."""
    # TODO: fetch from database
    return {
        "game_id": game_id,
        "status": "pending",
        "message": "Analysis not yet available",
    }


@router.get("/{game_id}/critical-moments")
async def get_critical_moments(game_id: str):
    """Get critical moments for an analyzed game."""
    # TODO: fetch from database
    return {
        "game_id": game_id,
        "critical_moments": [],
    }
