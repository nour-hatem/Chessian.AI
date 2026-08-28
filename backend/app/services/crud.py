"""Database CRUD operations for games and analyses."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Integer,
    and_,
    case,
    cast,
    delete,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Game, GameAnalysis, MoveAnalysis, MoveExplanation, User


# ---------- Identity helpers ----------

# Time-control buckets. Platform imports store a word ("blitz"), PGN uploads
# store the raw header ("600+0"), so each bucket matches either form.
_TIME_CONTROL_BUCKETS = {
    "bullet": (None, 180),
    "blitz": (180, 600),
    "rapid": (600, 1800),
    "classical": (1800, None),
}

_TIME_CONTROL_WORDS = {
    "bullet": ["bullet", "ultrabullet"],
    "blitz": ["blitz"],
    "rapid": ["rapid"],
    "classical": ["classical", "daily", "correspondence"],
}


def _time_control_condition(bucket: str):
    """Build a filter matching one time-control bucket across both vocabularies.

    Platform games store a speed word; PGN uploads store "<base>+<inc>" in
    seconds. ``substring(tc, '^[0-9]+')`` yields NULL for the word form, so the
    numeric comparison simply doesn't match those rows.
    """
    key = (bucket or "").strip().lower()
    if key not in _TIME_CONTROL_BUCKETS:
        return None

    lo, hi = _TIME_CONTROL_BUCKETS[key]
    base = cast(func.substring(Game.time_control, r"^[0-9]+"), Integer)

    numeric = []
    if lo is not None:
        numeric.append(base >= lo)
    if hi is not None:
        numeric.append(base < hi)

    return or_(
        func.lower(Game.time_control).in_(_TIME_CONTROL_WORDS[key]),
        and_(*numeric),
    )


async def resolve_user_usernames(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list[str]:
    """Return the platform usernames belonging to this user, lowercased.

    Prefers the explicit ``User.chesscom_username`` / ``lichess_username``
    columns. When neither is set — true for anything imported before those
    fields were persisted — falls back to inferring the name that appears most
    often across the user's own games. The owner plays in every game they
    import while opponents vary, so the modal username is reliably theirs.
    """
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()

    explicit = []
    if user is not None:
        for name in (user.chesscom_username, user.lichess_username):
            if name:
                explicit.append(name.lower())
    if explicit:
        return explicit

    # Fallback: modal username across both colours.
    whites = select(Game.white_username.label("name")).where(
        Game.user_id == user_id, Game.white_username.is_not(None)
    )
    blacks = select(Game.black_username.label("name")).where(
        Game.user_id == user_id, Game.black_username.is_not(None)
    )
    both = union_all(whites, blacks).subquery()

    stmt = (
        select(func.lower(both.c.name).label("name"), func.count().label("n"))
        .group_by(func.lower(both.c.name))
        .order_by(func.count().desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    return [row.name] if row and row.name else []


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
    result: str | None = None,
    analyzed: str | None = None,
    time_control: str | None = None,
    opening_eco: str | None = None,
    usernames: list[str] | None = None,
) -> tuple[list[Game], int]:
    """List games with pagination, filtering, and search. Returns (games, total).

    Filters
    -------
    source        exact match on import source
    search        ILIKE across opening name and both player names
    result        "win" / "loss" / "draw" from the library owner's perspective
                  (needs ``usernames``; ignored when the side is unknown)
    analyzed      "yes" (analysis complete) / "no" (never analyzed or still
                  pending/processing) / "failed"
    time_control  "bullet" / "blitz" / "rapid" / "classical"
    opening_eco   exact ECO code, used by the openings → library drill-down
    """
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

    if opening_eco:
        base = base.where(Game.opening_eco == opening_eco)

    if time_control:
        cond = _time_control_condition(time_control)
        if cond is not None:
            base = base.where(cond)

    if result:
        key = result.strip().lower()
        names = [u.lower() for u in (usernames or [])]
        if names and key in ("win", "loss", "draw"):
            is_white = func.lower(Game.white_username).in_(names)
            is_black = func.lower(Game.black_username).in_(names)
            if key == "draw":
                base = base.where(Game.result == "1/2-1/2")
            elif key == "win":
                base = base.where(
                    or_(
                        and_(is_white, Game.result == "1-0"),
                        and_(is_black, Game.result == "0-1"),
                    )
                )
            else:
                base = base.where(
                    or_(
                        and_(is_white, Game.result == "0-1"),
                        and_(is_black, Game.result == "1-0"),
                    )
                )

    if analyzed:
        key = analyzed.strip().lower()
        complete_ids = select(GameAnalysis.game_id).where(
            GameAnalysis.status == "complete"
        )
        failed_ids = select(GameAnalysis.game_id).where(
            GameAnalysis.status == "failed"
        )
        if key in ("yes", "true", "analyzed"):
            base = base.where(Game.id.in_(complete_ids))
        elif key in ("no", "false", "unanalyzed"):
            base = base.where(Game.id.not_in(complete_ids))
        elif key == "failed":
            base = base.where(Game.id.in_(failed_ids))

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
    result_rows = await db.execute(stmt)
    games = list(result_rows.scalars().all())

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
        .order_by(
            MoveAnalysis.move_number,
            case({"white": 0, "black": 1}, value=MoveAnalysis.color),  # BUG-08 fix: white before black
        )
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
    analysis.opening_accuracy = analysis_data.get("opening_accuracy")
    analysis.middlegame_accuracy = analysis_data.get("middlegame_accuracy")
    analysis.endgame_accuracy = analysis_data.get("endgame_accuracy")
    analysis.critical_moments = analysis_data.get("critical_moments")
    analysis.status = "complete"
    analysis.completed_at = datetime.now(timezone.utc)

    # BUG-16 fix: delete old move analyses before re-inserting
    await db.execute(delete(MoveAnalysis).where(MoveAnalysis.game_id == game_id))

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
            tactical_motifs=mv.get("tactical_motifs"),  # BUG-19 fix
            time_spent=mv.get("time_spent"),  # BUG-19 fix
        )
        db.add(move_analysis)

    await db.flush()
    return analysis


# ---------- Explanations ----------

async def save_move_explanation(
    db: AsyncSession,
    move_analysis_id: uuid.UUID,
    explanation: str,
    model_used: str,
) -> MoveExplanation:
    """
    Persist an LLM-generated explanation for a single move.

    Uses INSERT ... ON CONFLICT DO NOTHING rather than catching IntegrityError.
    The previous version rolled the session back on a duplicate, which also
    discarded every explanation added earlier in the caller's loop (they are
    committed once, after the loop). A conflicting insert is now a no-op and
    the existing row is returned.
    """
    stmt = (
        pg_insert(MoveExplanation)
        .values(
            id=uuid.uuid4(),
            move_analysis_id=move_analysis_id,
            explanation=explanation,
            model_used=model_used,
            generated_at=datetime.now(timezone.utc),
        )
        .on_conflict_do_nothing(index_elements=["move_analysis_id"])
    )
    await db.execute(stmt)

    existing = await db.execute(
        select(MoveExplanation).where(
            MoveExplanation.move_analysis_id == move_analysis_id
        )
    )
    return existing.scalar_one()


async def get_explanations_for_game(
    db: AsyncSession,
    game_id: uuid.UUID,
) -> dict[uuid.UUID, str]:
    """
    Return all LLM explanations for a game as {move_analysis_id: explanation_text}.

    Joins MoveExplanation → MoveAnalysis filtered by game_id.
    """
    stmt = (
        select(MoveExplanation)
        .join(MoveAnalysis, MoveExplanation.move_analysis_id == MoveAnalysis.id)
        .where(MoveAnalysis.game_id == game_id)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {row.move_analysis_id: row.explanation for row in rows}


# ---------- Opening Profiler ----------

async def get_opening_repertoire(
    db: AsyncSession,
    user_id: uuid.UUID,
    usernames: list[str],
    *,
    min_games: int = 3,
) -> list[dict]:
    """
    Aggregate per-opening stats across all analyzed games for a user.

    Joins Game -> GameAnalysis, groups by ECO + opening name, and reports
    wins/losses/draws **from the user's own perspective** along with the
    accuracy of the side the user actually played.

    ``usernames`` must be lowercased (see ``resolve_user_usernames``). When it
    is empty the user's colour cannot be determined, so accuracy and W/L/D are
    returned as None/0 rather than silently attributing every game to Black —
    which is what the previous exact, case-sensitive comparison against a
    hardcoded fallback name did.
    """
    names = [u.lower() for u in (usernames or [])]

    if names:
        is_white = func.lower(Game.white_username).in_(names)
        is_black = func.lower(Game.black_username).in_(names)

        user_accuracy_expr = case(
            (is_white, GameAnalysis.white_accuracy),
            (is_black, GameAnalysis.black_accuracy),
        )
        opp_accuracy_expr = case(
            (is_white, GameAnalysis.black_accuracy),
            (is_black, GameAnalysis.white_accuracy),
        )
        win_expr = case(
            (and_(is_white, Game.result == "1-0"), 1),
            (and_(is_black, Game.result == "0-1"), 1),
            else_=0,
        )
        loss_expr = case(
            (and_(is_white, Game.result == "0-1"), 1),
            (and_(is_black, Game.result == "1-0"), 1),
            else_=0,
        )
        white_games_expr = case((is_white, 1), else_=0)
    else:
        user_accuracy_expr = literal(None)
        opp_accuracy_expr = literal(None)
        win_expr = literal(0)
        loss_expr = literal(0)
        white_games_expr = literal(0)

    draw_expr = case((Game.result == "1/2-1/2", 1), else_=0)

    stmt = (
        select(
            Game.opening_eco,
            Game.opening_name,
            func.count().label("games_played"),
            func.sum(win_expr).label("wins"),
            func.sum(loss_expr).label("losses"),
            func.sum(draw_expr).label("draws"),
            func.sum(white_games_expr).label("games_as_white"),
            func.avg(user_accuracy_expr).label("avg_user_accuracy"),
            func.avg(opp_accuracy_expr).label("avg_opponent_accuracy"),
        )
        .join(GameAnalysis, Game.id == GameAnalysis.game_id)
        .where(
            Game.user_id == user_id,
            GameAnalysis.status == "complete",
        )
        .group_by(Game.opening_eco, Game.opening_name)
        .having(func.count() >= min_games)
        .order_by(func.count().desc())
    )

    rows = (await db.execute(stmt)).all()

    openings = []
    for row in rows:
        games = row.games_played or 0
        wins = int(row.wins or 0)
        losses = int(row.losses or 0)
        draws = int(row.draws or 0)

        avg_user = (
            round(float(row.avg_user_accuracy), 1)
            if row.avg_user_accuracy is not None
            else None
        )
        avg_opp = (
            round(float(row.avg_opponent_accuracy), 1)
            if row.avg_opponent_accuracy is not None
            else None
        )

        # Score from the user's perspective: a draw counts as half a point.
        decided = wins + losses + draws
        score_pct = (
            round(((wins + 0.5 * draws) / decided) * 100, 1) if decided else None
        )

        openings.append({
            "eco": row.opening_eco or "",
            "name": row.opening_name or "Unknown",
            "games_played": games,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "games_as_white": int(row.games_as_white or 0),
            "games_as_black": games - int(row.games_as_white or 0),
            "score_pct": score_pct,
            "avg_user_accuracy": avg_user,
            "avg_opponent_accuracy": avg_opp,
        })

    return openings
