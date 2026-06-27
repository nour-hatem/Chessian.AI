import asyncio
import logging
from dataclasses import asdict
from app.database import async_session
from app.config import settings
from app.models import Game, GameAnalysis
from app.services import crud
from app.services.analyzer import analyze_game
from sqlalchemy import select

async def migrate():
    async with async_session() as db:
        games = (await db.execute(select(Game))).scalars().all()
        print(f"Total games to analyze: {len(games)}")
        
        for i, game in enumerate(games):
            try:
                existing = await crud.get_game_analysis(db, game.id)
                if not existing:
                    await crud.create_game_analysis(db, game.id, 5)
                    await db.commit()
                elif existing.status == "complete":
                    continue

                print(f"[{i+1}/{len(games)}] Analyzing {game.id}")
                result = await analyze_game(game.pgn, settings.stockfish_path, depth=5)
                
                critical_moments = [
                    {
                        "move_number": m.move_number,
                        "color": m.color,
                        "move_san": m.move_san,
                        "cp_loss": m.cp_loss,
                        "classification": m.classification,
                    }
                    for m in result.moves if m.is_critical_moment
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
                await crud.save_analysis_results(db, game.id, analysis_data, move_evals)
                await db.commit()
            except Exception as e:
                print(f"Skipping game {game.id} due to error: {e}")
                existing = await crud.get_game_analysis(db, game.id)
                if existing:
                    existing.status = "failed"
                    await db.commit()

asyncio.run(migrate())
