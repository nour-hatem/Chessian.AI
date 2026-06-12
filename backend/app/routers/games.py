"""Games router — CRUD operations for the game library."""

from fastapi import APIRouter, HTTPException, Query
from app.schemas import GameResponse, GameListResponse

router = APIRouter()

# In-memory store for development (replaced with DB in production)
_games_store: list[dict] = []


@router.get("", response_model=GameListResponse)
async def list_games(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: str | None = None,
    search: str | None = None,
):
    """List all games in the user's library with pagination and filtering."""
    filtered = _games_store

    if source:
        filtered = [g for g in filtered if g.get("source") == source]

    if search:
        q = search.lower()
        filtered = [
            g for g in filtered
            if q in g.get("opening_name", "").lower()
            or q in g.get("white_username", "").lower()
            or q in g.get("black_username", "").lower()
        ]

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = filtered[start:end]

    return GameListResponse(
        games=[GameResponse(**g, has_analysis=False) for g in paginated],
        total=total,
    )


@router.get("/{game_id}")
async def get_game(game_id: str):
    """Get a single game by ID."""
    for g in _games_store:
        if str(g.get("id")) == game_id:
            return g
    raise HTTPException(status_code=404, detail="Game not found")
