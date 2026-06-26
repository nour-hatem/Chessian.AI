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


@router.get("", response_model=GameListResponse)
async def list_games(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    source: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all games in the user's library with pagination and filtering."""
    user_id = await ensure_dev_user(db)
    games, total = await crud.list_games(
        db,
        user_id,
        page=page,
        per_page=per_page,
        source=source,
        search=search,
    )

    return GameListResponse(
        games=[
            GameResponse(
                id=g.id,
                source=g.source,
                white_username=g.white_username,
                black_username=g.black_username,
                result=g.result,
                time_control=g.time_control,
                opening_eco=g.opening_eco,
                opening_name=g.opening_name,
                played_at=g.played_at,
                imported_at=g.imported_at,
                has_analysis=g.analysis is not None and g.analysis.status == "complete",
            )
            for g in games
        ],
        total=total,
    )

@router.get("/openings/repertoire")
async def get_opening_repertoire(
    db: AsyncSession = Depends(get_db),
):
    """Get opening repertoire stats aggregated across all analyzed games.

    Returns one entry per opening (ECO + name) that appears in at least
    3 analyzed games, with result counts and average accuracies.
    """
    from sqlalchemy import select
    from app.models import User
    user_id = await ensure_dev_user(db)
    user_obj = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    
    # Fallback to nourelhashash for dev if platform usernames aren't set
    username = "nourelhashash"
    if user_obj:
        username = user_obj.chesscom_username or user_obj.lichess_username or "nourelhashash"
    
    data = await crud.get_opening_repertoire(db, user_id, username)
    return {"openings": data, "total": len(data)}


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
        has_analysis=game.analysis is not None and game.analysis.status == "complete",
    )


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
