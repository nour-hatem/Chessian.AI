"""Analysis router — triggers and retrieves game analyses."""

import logging
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, async_session
from app.schemas import GameAnalysisResponse, MoveAnalysisResponse
from app.services import crud
from app.services.auth import ensure_dev_user
from app.services.analyzer import analyze_game
from app.services.explainer import explain_move

router = APIRouter()
logger = logging.getLogger(__name__)


async def _run_analysis_background(game_id: uuid.UUID, pgn: str, depth: int):
    """Run Stockfish analysis in the background and save results."""
    async with async_session() as db:
        try:
            # Update status to processing
            analysis = await crud.get_game_analysis(db, game_id)
            if analysis:
                analysis.status = "processing"
                await db.commit()

            # Run engine analysis
            result = await analyze_game(
                pgn,
                stockfish_path=settings.stockfish_path,
                depth=depth,
            )

            # Prepare data for persistence
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

            if settings.groq_api_key:
                move_rows = await crud.get_move_analyses(db, game_id)
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
                await db.commit()
            else:
                logger.warning("GROQ_API_KEY not set — skipping explanation generation")

        except Exception as e:
            # C1 fix: rollback the broken transaction before recovery query
            await db.rollback()
            logger.exception("Background analysis failed for game %s: %s", game_id, e)
            try:
                analysis = await crud.get_game_analysis(db, game_id)
                if analysis:
                    analysis.status = "failed"
                    await db.commit()
            except Exception:
                logger.exception("Failed to mark analysis as failed for game %s", game_id)


@router.post("/{game_id}")
async def trigger_analysis(
    game_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    depth: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Trigger Stockfish analysis for a game."""
    user_id = await ensure_dev_user(db)
    # Verify game exists and belongs to user
    game = await crud.get_game(db, game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if analysis already exists
    existing = await crud.get_game_analysis(db, game_id)
    if existing and existing.status in ("complete", "processing"):
        return {
            "game_id": str(game_id),
            "status": existing.status,
            "message": f"Analysis already {existing.status}",
        }

    # Create analysis record (or reuse/reset a failed one)
    if existing is None:
        await crud.create_game_analysis(db, game_id, depth)
        await db.commit()
    elif existing.status == "failed":
        # M4 fix: reset failed analysis so it can be retried
        existing.status = "pending"
        existing.analysis_depth = depth
        await db.commit()

    # Queue background analysis
    background_tasks.add_task(
        _run_analysis_background,
        game_id,
        game.pgn,
        depth,
    )

    return {
        "game_id": str(game_id),
        "status": "queued",
        "depth": depth,
        "message": "Analysis queued. Check status at GET /api/analysis/{game_id}",
    }


@router.get("/{game_id}", response_model=GameAnalysisResponse)
async def get_analysis(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get analysis results for a game."""
    user_id = await ensure_dev_user(db)
    # Verify game belongs to user
    game = await crud.get_game(db, game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    analysis = await crud.get_game_analysis(db, game_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found. Trigger it with POST first.")

    # Get move-level data if analysis is complete
    moves = []
    if analysis.status == "complete":
        move_rows = await crud.get_move_analyses(db, game_id)
        explanations = await crud.get_explanations_for_game(db, game_id)
        moves = [
            MoveAnalysisResponse(
                move_number=m.move_number,
                color=m.color,
                move_san=m.move_san,
                eval_before=m.eval_before,
                eval_after=m.eval_after,
                cp_loss=m.cp_loss,
                classification=m.classification,
                best_move_san=m.best_move_san,
                is_critical_moment=m.is_critical_moment,
                time_spent=m.time_spent,
                explanation=explanations.get(m.id),
            )
            for m in move_rows
        ]

    return GameAnalysisResponse(
        game_id=game_id,
        status=analysis.status,
        white_accuracy=analysis.white_accuracy,
        black_accuracy=analysis.black_accuracy,
        white_blunders=analysis.white_blunders or 0,
        white_mistakes=analysis.white_mistakes or 0,
        white_inaccuracies=analysis.white_inaccuracies or 0,
        black_blunders=analysis.black_blunders or 0,
        black_mistakes=analysis.black_mistakes or 0,
        black_inaccuracies=analysis.black_inaccuracies or 0,
        opening_accuracy=analysis.opening_accuracy,
        middlegame_accuracy=analysis.middlegame_accuracy,
        endgame_accuracy=analysis.endgame_accuracy,
        moves=moves,
    )


@router.get("/{game_id}/critical-moments")
async def get_critical_moments(
    game_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get critical moments for an analyzed game."""
    user_id = await ensure_dev_user(db)
    game = await crud.get_game(db, game_id, user_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    analysis = await crud.get_game_analysis(db, game_id)
    if analysis is None or analysis.status != "complete":
        raise HTTPException(status_code=404, detail="Analysis not complete")

    return {
        "game_id": str(game_id),
        "critical_moments": analysis.critical_moments or [],
    }
