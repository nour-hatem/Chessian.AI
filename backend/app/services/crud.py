"""Database CRUD operations for games and analyses."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Game, GameAnalysis, MoveAnalysis


# ---------- Games ----------

async def create_game(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    source: str,
    pgn: str,
    moves_hash: str | None = None,
    white_username: str | None = None,
    black_username: str | None = None,
    result: str | None = None,
    time_control: str | None = None,
    opening_eco: str | None = None,
    opening_name: str | None = None,
    played_at: datetime | None = None,
    clock_data: dict | None = None,
) -> Game:
    """Insert a new game into the database."""
    game = Game(
        id=uuid.uuid4(),
        user_id=user_id,
        source=source,
        pgn=pgn,
        moves_hash=moves_hash,
        white_username=white_username,
        black_username=black_username,
        result=result,
        time_control=time_control,
        opening_eco=opening_eco,
        opening_name=opening_name,
        played_at=played_at,
        clock_data=clock_data,
        imported_at=datetime.now(timezone.utc),
    )
    db.add(game)
    await db.flush()
    return game


async def game_exists_by_hash(
    db: AsyncSession,
    user_id: uuid.UUID,
    moves_hash: str,
) -> bool:
    """Check if a game with this move hash already exists for the user."""
    stmt = select(Game.id).where(
        Game.user_id == user_id,
        Game.moves_hash == moves_hash,
    ).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_games(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    page: int = 1,
    per_page: int = 20,
    source: str | None = None,
    search: str | None = None,
) -> tuple[list[Game], int]:
    """List games with pagination, filtering, and search. Returns (games, total)."""
    base = select(Game).where(Game.user_id == user_id)

    if source:
        base = base.where(Game.source == source)

    if search:
        q = f"%{search}%"
        base = base.where(
            or_(
                Game.opening_name.ilike(q),
                Game.white_username.ilike(q),
                Game.black_username.ilike(q),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Paginated results
    stmt = (
        base
        .options(selectinload(Game.analysis))
        .order_by(Game.played_at.desc().nullslast(), Game.imported_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    games = list(result.scalars().all())

    return games, total


async def get_game(
    db: AsyncSession,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Game | None:
    """Get a single game by ID, scoped to user."""
    stmt = (
        select(Game)
        .options(selectinload(Game.analysis))
        .where(Game.id == game_id, Game.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_game_with_moves(
    db: AsyncSession,
    game_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Game | None:
    """Get a game with its full analysis and move-level data."""
    stmt = (
        select(Game)
        .options(
            selectinload(Game.analysis),
            selectinload(Game.move_analyses),
        )
        .where(Game.id == game_id, Game.user_id == user_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---------- Analysis ----------

async def create_game_analysis(
    db: AsyncSession,
    game_id: uuid.UUID,
    depth: int,
) -> GameAnalysis:
    """Create a pending analysis record for a game."""
    analysis = GameAnalysis(
        id=uuid.uuid4(),
        game_id=game_id,
        analysis_depth=depth,
        status="pending",
    )
    db.add(analysis)
    await db.flush()
    return analysis


async def get_game_analysis(
    db: AsyncSession,
    game_id: uuid.UUID,
) -> GameAnalysis | None:
    """Get the analysis record for a game."""
    stmt = select(GameAnalysis).where(GameAnalysis.game_id == game_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_move_analyses(
    db: AsyncSession,
    game_id: uuid.UUID,
) -> list[MoveAnalysis]:
    """Get all per-move analyses for a game, ordered by move number."""
    stmt = (
        select(MoveAnalysis)
        .where(MoveAnalysis.game_id == game_id)
        .order_by(MoveAnalysis.move_number, MoveAnalysis.color.desc())  # 'w' before 'b'
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save_analysis_results(
    db: AsyncSession,
    game_id: uuid.UUID,
    analysis_data: dict,
    move_evals: list[dict],
) -> GameAnalysis:
    """
    Save completed analysis results: update GameAnalysis + bulk insert MoveAnalysis rows.
    """
    # Update game analysis record
    analysis = await get_game_analysis(db, game_id)
    if analysis is None:
        raise ValueError(f"No analysis record for game {game_id}")

    analysis.white_accuracy = analysis_data.get("white_accuracy")
    analysis.black_accuracy = analysis_data.get("black_accuracy")
    analysis.white_blunders = analysis_data.get("white_blunders", 0)
    analysis.white_mistakes = analysis_data.get("white_mistakes", 0)
    analysis.white_inaccuracies = analysis_data.get("white_inaccuracies", 0)
    analysis.black_blunders = analysis_data.get("black_blunders", 0)
    analysis.black_mistakes = analysis_data.get("black_mistakes", 0)
    analysis.black_inaccuracies = analysis_data.get("black_inaccuracies", 0)
    analysis.critical_moments = analysis_data.get("critical_moments")
    analysis.status = "complete"
    analysis.completed_at = datetime.now(timezone.utc)

    # Bulk create move analysis records
    for mv in move_evals:
        move_analysis = MoveAnalysis(
            id=uuid.uuid4(),
            game_id=game_id,
            move_number=mv["move_number"],
            color=mv["color"],
            move_uci=mv.get("move_uci"),
            move_san=mv.get("move_san"),
            fen_before=mv.get("fen_before"),
            fen_after=mv.get("fen_after"),
            eval_before=mv.get("eval_before"),
            eval_after=mv.get("eval_after"),
            best_move_uci=mv.get("best_move_uci"),
            best_move_san=mv.get("best_move_san"),
            best_line=mv.get("best_line"),
            cp_loss=mv.get("cp_loss"),
            classification=mv.get("classification"),
            is_critical_moment=mv.get("is_critical_moment", False),
        )
        db.add(move_analysis)

    await db.flush()
    return analysis
