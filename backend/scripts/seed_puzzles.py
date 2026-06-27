"""
Seed puzzle database from a slice of the Lichess puzzle CSV.

Usage (run ONCE — idempotent on re-run via ON CONFLICT DO NOTHING):
    cd /home/nour/Chessian.AI/backend
    /home/nour/Chessian.AI/.venv/bin/python -m scripts.seed_puzzles

What it does:
    1. Downloads the Lichess puzzle CSV (compressed, ~80MB) via streaming.
    2. Reads rows until it has collected TARGET_COUNT puzzles uniformly
       distributed across RATING_BANDS (800-2200 Elo), ~500 per band.
    3. Bulk-inserts them into the puzzles table (ON CONFLICT DO NOTHING so
       re-running is safe — already-imported puzzles are skipped).
    4. Prints a final summary with row counts per rating band.

CSV format (Lichess):
    PuzzleId,FEN,Moves,Rating,RatingDeviation,Popularity,NbPlays,Themes,GameUrl,OpeningTags

Notes:
    - The compressed file is streamed and never fully materialised in memory.
    - zstandard (zstd) decompression is used — install with:
          pip install zstandard
    - If the download fails (no internet), the script exits cleanly with an
      error message and no DB changes are made.
"""

import asyncio
import csv
import io
import logging
import sys
import uuid
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_puzzles")

# Configuration
LICHESS_PUZZLE_CSV_URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"

# Rating bands: (min_inclusive, max_exclusive) → target count from this band
RATING_BANDS = [
    (800,  1000, 400),
    (1000, 1200, 500),
    (1200, 1400, 500),
    (1400, 1600, 500),
    (1600, 1800, 500),
    (1800, 2000, 400),
    (2000, 2200, 300),
]
TARGET_TOTAL = sum(n for _, _, n in RATING_BANDS)  # 3100 puzzles

BATCH_SIZE = 500   # rows per INSERT batch


def rating_band_index(rating: int) -> int | None:
    for i, (lo, hi, _) in enumerate(RATING_BANDS):
        if lo <= rating < hi:
            return i
    return None


async def run_seed():
    # Import here so the script fails fast if zstandard is not installed
    try:
        import zstandard as zstd
        import urllib.request
    except ImportError:
        logger.error("Missing dependency: pip install zstandard")
        sys.exit(1)

    from app.database import async_session
    from app.models import Puzzle

    # Check how many puzzles already exist
    from sqlalchemy import select, func as sqlfunc
    async with async_session() as db:
        count_result = await db.execute(select(sqlfunc.count()).select_from(Puzzle))
        existing = count_result.scalar_one()

    if existing >= TARGET_TOTAL:
        logger.info(
            "Puzzles table already has %d rows (>= target %d). Nothing to do.",
            existing, TARGET_TOTAL,
        )
        return

    logger.info("Streaming Lichess puzzle CSV from %s ...", LICHESS_PUZZLE_CSV_URL)
    logger.info("Target: %d puzzles across %d rating bands.", TARGET_TOTAL, len(RATING_BANDS))

    # Counters per band
    band_counts = defaultdict(int)
    band_targets = {i: n for i, (_, _, n) in enumerate(RATING_BANDS)}
    collected: list[dict] = []

    def is_full() -> bool:
        return all(band_counts[i] >= band_targets[i] for i in range(len(RATING_BANDS)))

    # Stream + decompress
    try:
        response = urllib.request.urlopen(LICHESS_PUZZLE_CSV_URL, timeout=60)
    except Exception as e:
        logger.error("Failed to connect to Lichess: %s", e)
        sys.exit(1)

    dctx = zstd.ZstdDecompressor()
    stream_reader = dctx.stream_reader(response)
    text_stream = io.TextIOWrapper(stream_reader, encoding="utf-8")
    reader = csv.DictReader(text_stream)

    rows_scanned = 0
    for row in reader:
        rows_scanned += 1
        if rows_scanned % 100_000 == 0:
            logger.info(
                "  Scanned %dk rows, collected %d/%d puzzles...",
                rows_scanned // 1000, len(collected), TARGET_TOTAL,
            )

        try:
            rating = int(row["Rating"])
        except (ValueError, KeyError):
            continue

        band_idx = rating_band_index(rating)
        if band_idx is None:
            continue
        if band_counts[band_idx] >= band_targets[band_idx]:
            continue

        # Parse themes and opening tags
        themes_raw = row.get("Themes", "").strip()
        themes = themes_raw.split() if themes_raw else []

        opening_raw = row.get("OpeningTags", "").strip()
        opening_tags = opening_raw.split() if opening_raw else []

        collected.append({
            "id": uuid.uuid4(),
            "lichess_id": row["PuzzleId"],
            "fen": row["FEN"],
            "moves": row["Moves"],
            "themes": themes if themes else None,
            "opening_tags": opening_tags if opening_tags else None,
            "rating": rating,
            "rating_deviation": int(row.get("RatingDeviation", 500) or 500),
            "popularity": int(row.get("Popularity", 0) or 0),
            "nb_plays": int(row.get("NbPlays", 0) or 0),
            "game_url": row.get("GameUrl") or None,
        })
        band_counts[band_idx] += 1

        if is_full():
            logger.info("All band targets met after scanning %d rows.", rows_scanned)
            break

    if not collected:
        logger.error("No puzzles collected — check CSV format or network access.")
        sys.exit(1)

    logger.info("Collected %d puzzles. Inserting into database...", len(collected))

    # Bulk insert in batches (ON CONFLICT DO NOTHING for idempotency)
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    inserted_total = 0

    async with async_session() as db:
        for start in range(0, len(collected), BATCH_SIZE):
            batch = collected[start : start + BATCH_SIZE]
            stmt = (
                pg_insert(Puzzle)
                .values(batch)
                .on_conflict_do_nothing(index_elements=["lichess_id"])
            )
            await db.execute(stmt)
            await db.commit()
            inserted_total += len(batch)
            logger.info("  Inserted batch %d–%d", start, start + len(batch) - 1)

    # Final summary
    logger.info("=" * 55)
    logger.info("SEED COMPLETE — %d puzzles inserted.", inserted_total)
    for i, (lo, hi, target) in enumerate(RATING_BANDS):
        logger.info("  %4d–%4d Elo: %d/%d", lo, hi - 1, band_counts[i], target)


if __name__ == "__main__":
    asyncio.run(run_seed())
