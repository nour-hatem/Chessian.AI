"""Games router — CRUD operations for the game library."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import GameResponse, GameListResponse
from app.services import crud
from app.services.auth import ensure_dev_user

router = APIRouter()


def _user_perspective(game, usernames: list[str]) -> tuple[str | None, str | None]:
    """Return (user_color, user_result) for a game, or (None, None) if unknown."""
    if not usernames:
        return None, None

    white = (game.white_username or "").lower()
    black = (game.black_username or "").lower()

    if white in usernames:
        color = "white"
    elif black in usernames:
        color = "black"
    else:
        return None, None

    if game.result == "1/2-1/2":
        return color, "draw"
    if game.result == "1-0":
        return color, "win" if color == "white" else "loss"
    if game.result == "0-1":
        return color, "win" if color == "black" else "loss"
    return color, None


def _to_response(game, usernames: list[str]) -> GameResponse:
    """Serialise a Game ORM row into the API response shape."""
    status = game.analysis.status if game.analysis is not None else None
    color, user_result = _user_perspective(game, usernames)
    return GameResponse(
        id=game.id,
        source=game.source,
        white_username=game.white_username,
        black_username=game.black_username,
        result=game.result,
        time_control=game.time_control,
        opening_eco=game.opening_eco,
        opening_name=game.opening_name,
        played_at=game.played_at,
        imported_at=game.imported_at,
        has_analysis=status == "complete",
        analysis_status=status,
        user_color=color,
        user_result=user_result,
    )


@router.get("", response_model=GameListResponse)
async def list_games(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: str | None = None,
    search: str | None = None,
    result: str | None = Query(None, description="win | loss | draw (user's perspective)"),
    analyzed: str | None = Query(None, description="yes | no | failed"),
    time_control: str | None = Query(None, description="bullet | blitz | rapid | classical"),
    opening_eco: str | None = Query(None, description="Exact ECO code"),
    db: AsyncSession = Depends(get_db),
):
    """List all games in the user's library with pagination and filtering."""
    user_id = await ensure_dev_user(db)
    usernames = await crud.resolve_user_usernames(db, user_id)

    games, total = await crud.list_games(
        db,
        user_id,
        page=page,
        per_page=per_page,
        source=source,
        search=search,
        result=result,
        analyzed=analyzed,
        time_control=time_control,
        opening_eco=opening_eco,
        usernames=usernames,
    )

    return GameListResponse(
        games=[_to_response(g, usernames) for g in games],
        total=total,
    )


@router.get("/openings/repertoire")
async def get_opening_repertoire(
    min_games: int = Query(3, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get opening repertoire stats aggregated across all analyzed games.

    Returns one entry per opening (ECO + name) that appears in at least
    ``min_games`` analyzed games, with W/L/D and accuracy reported from the
    user's own perspective.
    """
    user_id = await ensure_dev_user(db)
    usernames = await crud.resolve_user_usernames(db, user_id)
    data = await crud.get_opening_repertoire(
        db, user_id, usernames, min_games=min_games
    )
    return {
        "openings": data,
        "total": len(data),
        # Surfaced so the UI can explain *why* accuracy is missing rather than
        # rendering a table full of dashes with no reason given.
        "identity_resolved": bool(usernames),
    }


@router.get("/{game_id}")
async def get_game(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single game by ID."""
    user_id = await ensure_dev_user(db)
    game = await crud.get_game(db, game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    usernames = await crud.resolve_user_usernames(db, user_id)
    return _to_response(game, usernames)


@router.get("/{game_id}/pgn", response_class=PlainTextResponse)
async def get_game_pgn(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return the raw PGN text for a game."""
    user_id = await ensure_dev_user(db)
    game = await crud.get_game(db, game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.pgn
