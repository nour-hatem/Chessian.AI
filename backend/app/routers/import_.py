"""Import router — handles game imports from Chess.com, Lichess, and PGN files."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ImportRequest, ImportProgress
from app.services import crud
from app.services.auth import ensure_dev_user
from app.services.importer import (
    fetch_lichess_games,
    fetch_chesscom_games,
    parse_pgn_file,
    compute_moves_hash,
)

router = APIRouter()


def _parse_played_at(value) -> datetime | None:
    """Safely parse played_at from various formats."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        # Unix timestamp (Chess.com uses epoch seconds)
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        # Try ISO format
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y.%m.%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


@router.post("/lichess", response_model=ImportProgress)
async def import_from_lichess(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import games from Lichess for a given username."""
    user_id = await ensure_dev_user(db)
    games_imported = 0
    games_skipped = 0

    try:
        async for game_data in fetch_lichess_games(
            username=request.username,
            max_games=request.max_games,
        ):
            moves_hash = compute_moves_hash(game_data["pgn"])

            # Deduplicate
            if await crud.game_exists_by_hash(db, user_id, moves_hash):
                games_skipped += 1
                continue

            try:
                await crud.create_game(
                    db,
                    user_id=user_id,
                    source="lichess",
                    pgn=game_data["pgn"],
                    moves_hash=moves_hash,
                    white_username=game_data.get("white"),
                    black_username=game_data.get("black"),
                    result=game_data.get("result"),
                    time_control=game_data.get("time_control"),
                    opening_eco=game_data.get("opening_eco"),
                    opening_name=game_data.get("opening_name"),
                    played_at=_parse_played_at(game_data.get("played_at")),
                )
                await db.commit()
                games_imported += 1
            except Exception:
                await db.rollback()

        msg = f"Successfully imported {games_imported} games from Lichess"
        if games_skipped:
            msg += f" ({games_skipped} duplicates skipped)"

        return ImportProgress(
            status="complete",
            games_imported=games_imported,
            total_games=games_imported + games_skipped,
            message=msg,
        )
    except Exception as e:
        await db.rollback()
        return ImportProgress(
            status="failed",
            games_imported=games_imported,
            total_games=0,
            message=f"Import failed: {str(e)}",
        )


@router.post("/chesscom", response_model=ImportProgress)
async def import_from_chesscom(
    request: ImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import games from Chess.com for a given username."""
    user_id = await ensure_dev_user(db)
    games_imported = 0
    games_skipped = 0

    try:
        async for game_data in fetch_chesscom_games(
            username=request.username,
            max_games=request.max_games,
        ):
            moves_hash = compute_moves_hash(game_data["pgn"])

            # Deduplicate
            if await crud.game_exists_by_hash(db, user_id, moves_hash):
                games_skipped += 1
                continue

            try:
                await crud.create_game(
                    db,
                    user_id=user_id,
                    source="chesscom",
                    pgn=game_data["pgn"],
                    moves_hash=moves_hash,
                    white_username=game_data.get("white"),
                    black_username=game_data.get("black"),
                    result=game_data.get("result"),
                    time_control=game_data.get("time_control"),
                    opening_eco=game_data.get("opening_eco"),
                    opening_name=game_data.get("opening_name"),
                    played_at=_parse_played_at(game_data.get("played_at")),
                )
                await db.commit()
                games_imported += 1
            except Exception:
                await db.rollback()

        msg = f"Successfully imported {games_imported} games from Chess.com"
        if games_skipped:
            msg += f" ({games_skipped} duplicates skipped)"

        return ImportProgress(
            status="complete",
            games_imported=games_imported,
            total_games=games_imported + games_skipped,
            message=msg,
        )
    except Exception as e:
        await db.rollback()
        return ImportProgress(
            status="failed",
            games_imported=games_imported,
            total_games=0,
            message=f"Import failed: {str(e)}",
        )


@router.post("/pgn", response_model=ImportProgress)
async def import_from_pgn(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Import games from an uploaded PGN file."""
    user_id = await ensure_dev_user(db)
    # Limit upload to 10MB to prevent memory exhaustion
    max_size = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > max_size:
        return ImportProgress(
            status="failed",
            games_imported=0,
            total_games=0,
            message=f"File too large ({len(content) // (1024*1024)}MB). Maximum is 10MB.",
        )
    # C4 fix: Try UTF-8 first, then Latin-1 (common for European PGN files)
    try:
        pgn_text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            pgn_text = content.decode("latin-1")
        except UnicodeDecodeError:
            return ImportProgress(
                status="failed",
                games_imported=0,
                total_games=0,
                message="Unable to decode PGN file. Please ensure it is UTF-8 or Latin-1 encoded.",
            )

    games = parse_pgn_file(pgn_text)
    games_imported = 0
    games_skipped = 0

    for game_data in games:
        moves_hash = compute_moves_hash(game_data["pgn"])

        # Deduplicate
        if await crud.game_exists_by_hash(db, user_id, moves_hash):
            games_skipped += 1
            continue

        try:
            await crud.create_game(
                db,
                user_id=user_id,
                source="pgn_upload",
                pgn=game_data["pgn"],
                moves_hash=moves_hash,
                white_username=game_data.get("white"),
                black_username=game_data.get("black"),
                result=game_data.get("result"),
                time_control=game_data.get("time_control"),
                opening_eco=game_data.get("opening_eco"),
                opening_name=game_data.get("opening_name"),
                played_at=_parse_played_at(game_data.get("played_at")),
            )
            await db.commit()
            games_imported += 1
        except Exception:
            await db.rollback()

    msg = f"Successfully imported {games_imported} game(s) from PGN file"
    if games_skipped:
        msg += f" ({games_skipped} duplicates skipped)"

    return ImportProgress(
        status="complete",
        games_imported=games_imported,
        total_games=games_imported + games_skipped,
        message=msg,
    )
