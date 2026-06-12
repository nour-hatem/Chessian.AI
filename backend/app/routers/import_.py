"""Import router — handles game imports from Chess.com, Lichess, and PGN files."""

from fastapi import APIRouter, UploadFile, File
from app.schemas import ImportRequest, ImportProgress
from app.services.importer import (
    fetch_lichess_games,
    fetch_chesscom_games,
    parse_pgn_file,
    compute_moves_hash,
)

router = APIRouter()


@router.post("/lichess", response_model=ImportProgress)
async def import_from_lichess(request: ImportRequest):
    """Import games from Lichess for a given username."""
    games_imported = 0

    try:
        async for game_data in fetch_lichess_games(
            username=request.username,
            max_games=request.max_games,
        ):
            moves_hash = compute_moves_hash(game_data["pgn"])
            game_data["moves_hash"] = moves_hash
            # TODO: persist to database
            games_imported += 1

        return ImportProgress(
            status="complete",
            games_imported=games_imported,
            total_games=games_imported,
            message=f"Successfully imported {games_imported} games from Lichess",
        )
    except Exception as e:
        return ImportProgress(
            status="failed",
            games_imported=games_imported,
            total_games=0,
            message=f"Import failed: {str(e)}",
        )


@router.post("/chesscom", response_model=ImportProgress)
async def import_from_chesscom(request: ImportRequest):
    """Import games from Chess.com for a given username."""
    games_imported = 0

    try:
        async for game_data in fetch_chesscom_games(
            username=request.username,
            max_games=request.max_games,
        ):
            moves_hash = compute_moves_hash(game_data["pgn"])
            game_data["moves_hash"] = moves_hash
            # TODO: persist to database
            games_imported += 1

        return ImportProgress(
            status="complete",
            games_imported=games_imported,
            total_games=games_imported,
            message=f"Successfully imported {games_imported} games from Chess.com",
        )
    except Exception as e:
        return ImportProgress(
            status="failed",
            games_imported=games_imported,
            total_games=0,
            message=f"Import failed: {str(e)}",
        )


@router.post("/pgn", response_model=ImportProgress)
async def import_from_pgn(file: UploadFile = File(...)):
    """Import games from an uploaded PGN file."""
    content = await file.read()
    pgn_text = content.decode("utf-8", errors="replace")

    games = parse_pgn_file(pgn_text)

    for game_data in games:
        game_data["moves_hash"] = compute_moves_hash(game_data["pgn"])
        # TODO: persist to database

    return ImportProgress(
        status="complete",
        games_imported=len(games),
        total_games=len(games),
        message=f"Successfully imported {len(games)} game(s) from PGN file",
    )
