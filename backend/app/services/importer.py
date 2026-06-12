"""Import service — fetches games from Chess.com and Lichess APIs."""

import hashlib
from typing import AsyncGenerator

import httpx
import chess.pgn
import io


async def fetch_lichess_games(
    username: str,
    max_games: int = 100,
    token: str | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Stream games from Lichess API.

    Yields dicts with: pgn, white, black, result, time_control, opening, played_at.
    """
    url = f"https://lichess.org/api/games/user/{username}"
    params = {
        "max": max_games,
        "pgnInJson": "true",
        "clocks": "true",
        "opening": "true",
    }
    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("GET", url, params=params, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                import json

                game_data = json.loads(line)
                pgn_text = game_data.get("pgn", "")
                players = game_data.get("players", {})
                opening = game_data.get("opening", {})

                yield {
                    "pgn": pgn_text,
                    "white": players.get("white", {}).get("user", {}).get("name", "Unknown"),
                    "black": players.get("black", {}).get("user", {}).get("name", "Unknown"),
                    "result": _extract_result(game_data.get("winner")),
                    "time_control": game_data.get("speed", "unknown"),
                    "opening_eco": opening.get("eco", ""),
                    "opening_name": opening.get("name", ""),
                    "played_at": game_data.get("createdAt"),
                    "source": "lichess",
                }


async def fetch_chesscom_games(
    username: str,
    max_games: int = 100,
) -> AsyncGenerator[dict, None]:
    """
    Fetch games from Chess.com API.

    Chess.com organizes games by monthly archives.
    Yields dicts with: pgn, white, black, result, time_control, opening, played_at.
    """
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get list of monthly archives
        resp = await client.get(archives_url)
        resp.raise_for_status()
        archives = resp.json().get("archives", [])

        # Fetch from most recent archives first
        games_yielded = 0
        for archive_url in reversed(archives):
            if games_yielded >= max_games:
                break

            resp = await client.get(archive_url)
            resp.raise_for_status()
            games_list = resp.json().get("games", [])

            for game_data in reversed(games_list):
                if games_yielded >= max_games:
                    break

                pgn_text = game_data.get("pgn", "")
                white_player = game_data.get("white", {})
                black_player = game_data.get("black", {})

                yield {
                    "pgn": pgn_text,
                    "white": white_player.get("username", "Unknown"),
                    "black": black_player.get("username", "Unknown"),
                    "result": white_player.get("result", ""),
                    "time_control": game_data.get("time_class", "unknown"),
                    "opening_eco": _extract_eco_from_pgn(pgn_text),
                    "opening_name": _extract_opening_from_pgn(pgn_text),
                    "played_at": game_data.get("end_time"),
                    "source": "chesscom",
                }
                games_yielded += 1


def parse_pgn_file(pgn_text: str) -> list[dict]:
    """Parse a PGN file (may contain multiple games) and return game dicts."""
    games = []
    pgn_io = io.StringIO(pgn_text)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        headers = game.headers
        exporter = chess.pgn.StringExporter()
        pgn_str = game.accept(exporter)

        games.append({
            "pgn": pgn_str,
            "white": headers.get("White", "Unknown"),
            "black": headers.get("Black", "Unknown"),
            "result": headers.get("Result", "*"),
            "time_control": headers.get("TimeControl", "unknown"),
            "opening_eco": headers.get("ECO", ""),
            "opening_name": headers.get("Opening", ""),
            "played_at": headers.get("Date", ""),
            "source": "pgn_upload",
        })

    return games


def compute_moves_hash(pgn_text: str) -> str:
    """Compute SHA256 hash of the move sequence for deduplication."""
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        return hashlib.sha256(pgn_text.encode()).hexdigest()

    moves_str = " ".join(str(move) for move in game.mainline_moves())
    return hashlib.sha256(moves_str.encode()).hexdigest()


def _extract_result(winner: str | None) -> str:
    """Convert Lichess winner field to standard result."""
    if winner == "white":
        return "1-0"
    elif winner == "black":
        return "0-1"
    return "1/2-1/2"


def _extract_eco_from_pgn(pgn_text: str) -> str:
    """Extract ECO code from PGN headers."""
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game:
        return game.headers.get("ECO", "")
    return ""


def _extract_opening_from_pgn(pgn_text: str) -> str:
    """Extract opening name from PGN headers."""
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game:
        return game.headers.get("Opening", "")
    return ""
