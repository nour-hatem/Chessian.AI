"""
Re-analyze all games with a two-tier depth strategy + Groq LLM explanations.

Usage:
    cd /home/nour/Chessian.AI/backend
    /home/nour/Chessian.AI/.venv/bin/python -m scripts.reanalyze_all

Strategy:
    - First pass : every move evaluated at SCAN_DEPTH (14) — fast; used for
      cp_loss, classification, accuracy, and identifying critical moments.
    - Second pass: the ~5 critical moments re-evaluated at CRITICAL_DEPTH (20)
      so that eval / best_move / best_line sent to the LLM are deep and accurate.
    - GameAnalysis.analysis_depth is stored as CRITICAL_DEPTH (20) because the
      critical moments — the data most visible to the user — were computed at
      that depth. This also keeps the resumability filter (depth < 20) correct.

Resumability:
    Re-running picks up only games still at analysis_depth < 20.
"""

import asyncio
import logging
import sys
import time
from dataclasses import asdict

from sqlalchemy import select, or_

# -- Bootstrap app config + DB before importing services ----------------------
from app.config import settings
from app.database import async_session
from app.models import Game, GameAnalysis
from app.services import crud
from app.services.analyzer import analyze_game
from app.services.explainer import explain_move

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("reanalyze")

TARGET_DEPTH = 20   # stored as analysis_depth; keeps the resumability filter correct
SCAN_DEPTH = 14     # first-pass depth: every move (fast)
CRITICAL_DEPTH = 20 # second-pass depth: critical moments only (precise)


async def reanalyze_one(game_id, pgn: str, db) -> bool:
    """Re-analyze a single game. Returns True on success, False on failure."""
    # 1. Reset status
    analysis = await crud.get_game_analysis(db, game_id)
    if analysis is None:
        logger.warning("  No GameAnalysis row for %s — creating one", game_id)
        analysis = await crud.create_game_analysis(db, game_id, TARGET_DEPTH)
    analysis.status = "processing"
    analysis.analysis_depth = TARGET_DEPTH
    await db.commit()

    # 2. Run Stockfish — two-tier: scan all moves at SCAN_DEPTH, deepen the
    #    ~5 critical moments to CRITICAL_DEPTH for high-quality LLM context.
    result = await analyze_game(
        pgn,
        stockfish_path=settings.stockfish_path,
        depth=SCAN_DEPTH,
        critical_depth=CRITICAL_DEPTH,
    )

    # 3. Persist results (save_analysis_results deletes old MoveAnalysis rows,
    #    and CASCADE deletes linked MoveExplanation rows)
    critical_moments = [
        {
            "move_number": m.move_number,
            "color": m.color,
            "move_san": m.move_san,
            "cp_loss": m.cp_loss,
            "classification": m.classification,
        }
        for m in result.moves
        if m.is_critical_moment
    ]

    analysis_data = {
        "white_accuracy": result.white_accuracy,
        "black_accuracy": result.black_accuracy,
        "white_blunders": result.white_blunders,
        "white_mistakes": result.white_mistakes,
        "white_inaccuracies": result.white_inaccuracies,
        "black_blunders": result.black_blunders,
        "black_mistakes": result.black_mistakes,
        "black_inaccuracies": result.black_inaccuracies,
        "opening_accuracy": result.opening_accuracy,
        "middlegame_accuracy": result.middlegame_accuracy,
        "endgame_accuracy": result.endgame_accuracy,
        "critical_moments": critical_moments,
    }

    move_evals = [asdict(m) for m in result.moves]
    await crud.save_analysis_results(db, game_id, analysis_data, move_evals)
    await db.commit()

    # 4. Generate Groq explanations for critical moments
    move_rows = await crud.get_move_analyses(db, game_id)
    explanations_generated = 0
    for row in move_rows:
        if not row.is_critical_moment:
            continue
        if row.move_number <= 20:
            game_phase = "opening"
        elif row.move_number <= 60:
            game_phase = "middlegame"
        else:
            game_phase = "endgame"
        explanation = await explain_move(
            move_san=row.move_san or "",
            best_move_san=row.best_move_san or "",
            cp_loss=row.cp_loss or 0.0,
            classification=row.classification or "",
            eval_before=row.eval_before or 0.0,
            eval_after=row.eval_after or 0.0,
            fen_before=row.fen_before or "",
            game_phase=game_phase,
            groq_api_key=settings.groq_api_key,
        )
        if explanation:
            await crud.save_move_explanation(
                db, row.id, explanation, "llama-3.1-8b-instant"
            )
            explanations_generated += 1
    await db.commit()

    logger.info(
        "  ✓ %d moves analyzed, %d critical, %d explanations generated",
        len(result.moves),
        sum(1 for m in result.moves if m.is_critical_moment),
        explanations_generated,
    )
    return True


async def main():
    # ---- Pre-flight checks ----
    if not settings.groq_api_key:
        logger.error("GROQ_API_KEY is not set in .env — aborting.")
        sys.exit(1)
    logger.info("GROQ_API_KEY is set ✓")

    # ---- Discover games needing re-analysis ----
    async with async_session() as db:
        stmt = (
            select(GameAnalysis.game_id, GameAnalysis.analysis_depth)
            .where(
                or_(
                    GameAnalysis.analysis_depth < TARGET_DEPTH,
                    GameAnalysis.analysis_depth.is_(None),
                )
            )
            .order_by(GameAnalysis.game_id)
        )
        rows = (await db.execute(stmt)).all()

    total = len(rows)
    if total == 0:
        logger.info("All games are already at depth >= %d. Nothing to do.", TARGET_DEPTH)
        return

    logger.info(
        "Found %d games with analysis_depth < %d. Starting re-analysis...",
        total, TARGET_DEPTH,
    )

    passed = 0
    failed = 0
    start_time = time.monotonic()

    for idx, (game_id, old_depth) in enumerate(rows, 1):
        logger.info(
            "[%d/%d] Game %s  (current depth=%s → %d)",
            idx, total, game_id, old_depth, TARGET_DEPTH,
        )

        async with async_session() as db:
            # Fetch the game's PGN
            game_stmt = select(Game).where(Game.id == game_id)
            game = (await db.execute(game_stmt)).scalar_one_or_none()
            if game is None:
                logger.error("  Game %s not found in games table — skipping", game_id)
                failed += 1
                continue

            try:
                ok = await reanalyze_one(game_id, game.pgn, db)
                if ok:
                    passed += 1
                else:
                    failed += 1
            except Exception:
                await db.rollback()
                logger.exception("  ✗ FAILED for game %s", game_id)
                # Mark as failed so it's retried on next run
                try:
                    analysis = await crud.get_game_analysis(db, game_id)
                    if analysis:
                        analysis.status = "failed"
                        await db.commit()
                except Exception:
                    pass
                failed += 1

        elapsed = time.monotonic() - start_time
        avg = elapsed / idx
        remaining = avg * (total - idx)
        logger.info(
            "  Progress: %d/%d done (%.0fs elapsed, ~%.0fs remaining)",
            idx, total, elapsed, remaining,
        )

    elapsed_total = time.monotonic() - start_time
    logger.info("=" * 60)
    logger.info(
        "COMPLETE: %d passed, %d failed, %.1f minutes total",
        passed, failed, elapsed_total / 60,
    )


if __name__ == "__main__":
    asyncio.run(main())
