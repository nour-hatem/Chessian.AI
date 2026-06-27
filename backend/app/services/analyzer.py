"""Stockfish engine analysis service."""

import asyncio
import math
from dataclasses import dataclass, field

import chess
import chess.pgn
import chess.engine
import io

# Concurrency guard: only one Stockfish process at a time on this machine.
# Protects both the API-triggered path and standalone bulk scripts.
_engine_semaphore = asyncio.Semaphore(1)


@dataclass
class MoveEval:
    """Evaluation result for a single move."""
    move_number: int
    color: str  # "white" or "black"
    move_uci: str
    move_san: str
    fen_before: str
    fen_after: str
    eval_before: float  # centipawns
    eval_after: float
    best_move_uci: str
    best_move_san: str
    best_line: str  # PV as space-separated UCI
    cp_loss: float
    classification: str
    is_critical_moment: bool = False
    clock_time: float | None = None   # remaining clock time in seconds
    time_spent: float | None = None   # seconds spent on this move


@dataclass
class GameEvalResult:
    """Full game evaluation result."""
    moves: list[MoveEval] = field(default_factory=list)
    white_accuracy: float = 0.0
    black_accuracy: float = 0.0
    white_blunders: int = 0
    white_mistakes: int = 0
    white_inaccuracies: int = 0
    black_blunders: int = 0
    black_mistakes: int = 0
    black_inaccuracies: int = 0
    opening_accuracy: float | None = None
    middlegame_accuracy: float | None = None
    endgame_accuracy: float | None = None


def classify_move(cp_loss: float, is_best_move: bool = False) -> str:
    """Classify a move based on centipawn loss."""
    if cp_loss < 0:
        return "brilliant"  # Move improved eval beyond best line (rare, depth variance)
    if cp_loss == 0 or is_best_move:
        return "best"
    elif cp_loss < 25:
        return "good"
    elif cp_loss < 100:
        return "inaccuracy"
    elif cp_loss < 300:
        return "mistake"
    else:
        return "blunder"


def compute_accuracy(acpl: float) -> float:
    """
    Convert average centipawn loss to accuracy percentage.
    Uses the formula: accuracy = 103.1668 * exp(-0.04354 * ACPL) - 3.1668
    """
    if acpl <= 0:
        return 100.0
    accuracy = 103.1668 * math.exp(-0.04354 * acpl) - 3.1668
    return max(0.0, min(100.0, accuracy))


def _score_to_cp(score: chess.engine.PovScore) -> float:
    """Convert engine score to centipawns from white's perspective."""
    pov = score.white()
    if pov.is_mate():
        # Large values for mate scores; correctly handles mate in 0
        return 1000.0 if pov > chess.engine.Cp(0) else -1000.0
    cp = pov.score()
    return float(cp) if cp is not None else 0.0


async def analyze_game(
    pgn_text: str,
    stockfish_path: str = "/usr/bin/stockfish",
    depth: int = 20,
    critical_depth: int = 20,
) -> GameEvalResult:
    """
    Analyze a complete game with Stockfish using a two-tier depth strategy.

    First pass: every move is evaluated at `depth` (fast scan — used for
    cp_loss, classification, accuracy, and identifying critical moments).

    Second pass: the top critical moments (up to 5 positions with cp_loss > 50)
    are re-evaluated at `critical_depth` so that their eval / best_move /
    best_line are as precise as possible before being sent to the LLM.

    When called from the API (depth=20, critical_depth=20) behaviour is
    identical to the original single-pass approach.
    """
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        raise ValueError("Invalid PGN")

    result = GameEvalResult()
    board = game.board()

    # Pre-extract clock times from PGN nodes for time usage analysis (B7)
    clock_times: list[float | None] = []
    for node in game.mainline():
        clk = node.clock()
        clock_times.append(clk)

    async with _engine_semaphore:
        transport, engine = await chess.engine.popen_uci(stockfish_path)
        await engine.configure({"Threads": 6, "Hash": 512})

        try:
            white_cp_losses: list[float] = []
            black_cp_losses: list[float] = []
            white_prev_clock: float | None = None
            black_prev_clock: float | None = None

            # Evaluate the starting position once — this gives us eval + best move
            prev_info = await engine.analyse(board, chess.engine.Limit(depth=depth))
            prev_eval_white = _score_to_cp(prev_info["score"])

            for node in game.mainline():
                move = node.move
                color = "white" if board.turn == chess.WHITE else "black"
                move_number = board.fullmove_number

                fen_before = board.fen()
                move_san = board.san(move)
                move_uci = move.uci()

                # H1 fix: reuse prev_info for best move data (no extra engine call)
                eval_before = prev_eval_white
                best_move = prev_info.get("pv", [None])[0]
                best_move_san = board.san(best_move) if best_move else ""
                best_move_uci = best_move.uci() if best_move else ""
                pv = prev_info.get("pv", [])
                best_line = " ".join(m.uci() for m in pv[:5])

                # Make the move
                board.push(move)
                fen_after = board.fen()

                # Single engine call per move: evaluate the position after the move
                info_after = await engine.analyse(board, chess.engine.Limit(depth=depth))
                eval_after_white = _score_to_cp(info_after["score"])

                # Compute centipawn loss (from the moving side's perspective)
                if color == "white":
                    cp_loss = max(0, eval_before - eval_after_white)
                else:
                    cp_loss = max(0, eval_after_white - eval_before)

                is_best = best_move is not None and move == best_move
                classification = classify_move(cp_loss, is_best_move=is_best)

                # B7: extract clock time and compute time spent
                move_idx = len(result.moves)
                clk = clock_times[move_idx] if move_idx < len(clock_times) else None
                time_spent: float | None = None
                if clk is not None:
                    if color == "white":
                        if white_prev_clock is not None:
                            time_spent = max(0.0, white_prev_clock - clk)
                        white_prev_clock = clk
                    else:
                        if black_prev_clock is not None:
                            time_spent = max(0.0, black_prev_clock - clk)
                        black_prev_clock = clk

                move_eval = MoveEval(
                    move_number=move_number,
                    color=color,
                    move_uci=move_uci,
                    move_san=move_san,
                    fen_before=fen_before,
                    fen_after=fen_after,
                    eval_before=eval_before,
                    eval_after=eval_after_white,
                    best_move_uci=best_move_uci,
                    best_move_san=best_move_san,
                    best_line=best_line,
                    cp_loss=cp_loss,
                    classification=classification,
                    clock_time=clk,
                    time_spent=time_spent,
                )
                result.moves.append(move_eval)

                # Track losses per color
                if color == "white":
                    white_cp_losses.append(cp_loss)
                    if classification == "blunder":
                        result.white_blunders += 1
                    elif classification == "mistake":
                        result.white_mistakes += 1
                    elif classification == "inaccuracy":
                        result.white_inaccuracies += 1
                else:
                    black_cp_losses.append(cp_loss)
                    if classification == "blunder":
                        result.black_blunders += 1
                    elif classification == "mistake":
                        result.black_mistakes += 1
                    elif classification == "inaccuracy":
                        result.black_inaccuracies += 1

                # Carry forward for next iteration
                prev_eval_white = eval_after_white
                prev_info = info_after

            # Compute accuracy
            if white_cp_losses:
                white_acpl = sum(white_cp_losses) / len(white_cp_losses)
                result.white_accuracy = compute_accuracy(white_acpl)
            if black_cp_losses:
                black_acpl = sum(black_cp_losses) / len(black_cp_losses)
                result.black_accuracy = compute_accuracy(black_acpl)

            # BUG-18 fix: Compute phase-separated accuracy
            total_moves = len(result.moves)
            if total_moves > 0:
                opening_end = min(20, total_moves)  # First ~10 moves (20 half-moves)
                endgame_start = max(opening_end, total_moves - 20)  # Last ~10 moves

                opening_losses = [m.cp_loss for m in result.moves[:opening_end]]
                middle_losses = [m.cp_loss for m in result.moves[opening_end:endgame_start]]
                endgame_losses = [m.cp_loss for m in result.moves[endgame_start:]]

                if opening_losses:
                    result.opening_accuracy = compute_accuracy(
                        sum(opening_losses) / len(opening_losses)
                    )
                if middle_losses:
                    result.middlegame_accuracy = compute_accuracy(
                        sum(middle_losses) / len(middle_losses)
                    )
                if endgame_losses:
                    result.endgame_accuracy = compute_accuracy(
                        sum(endgame_losses) / len(endgame_losses)
                    )

            # Mark critical moments (top 5 highest cp_loss moves)
            sorted_moves = sorted(result.moves, key=lambda m: m.cp_loss, reverse=True)
            for m in sorted_moves[:5]:
                if m.cp_loss > 50:
                    m.is_critical_moment = True

            # ── Second pass: deepen critical moments only ─────────────────────
            # Re-analyse the ~5 critical positions at critical_depth so the
            # eval / best_move / best_line stored and sent to the LLM are as
            # accurate as possible, without paying that cost on every move.
            if critical_depth > depth:
                for m in result.moves:
                    if not m.is_critical_moment:
                        continue

                    # Re-evaluate the position *before* the played move
                    board_before = chess.Board(m.fen_before)
                    info_before_deep = await engine.analyse(
                        board_before, chess.engine.Limit(depth=critical_depth)
                    )
                    new_eval_before = _score_to_cp(info_before_deep["score"])
                    best_move_deep = info_before_deep.get("pv", [None])[0]
                    new_best_move_san = (
                        board_before.san(best_move_deep) if best_move_deep else ""
                    )
                    new_best_move_uci = (
                        best_move_deep.uci() if best_move_deep else ""
                    )
                    pv_deep = info_before_deep.get("pv", [])
                    new_best_line = " ".join(mv.uci() for mv in pv_deep[:5])

                    # Re-evaluate the position *after* the played move
                    board_after = chess.Board(m.fen_after)
                    info_after_deep = await engine.analyse(
                        board_after, chess.engine.Limit(depth=critical_depth)
                    )
                    new_eval_after = _score_to_cp(info_after_deep["score"])

                    # Recompute cp_loss at deeper depth
                    if m.color == "white":
                        new_cp_loss = max(0.0, new_eval_before - new_eval_after)
                    else:
                        new_cp_loss = max(0.0, new_eval_after - new_eval_before)

                    # Overwrite the shallow-pass values on this MoveEval
                    m.eval_before = new_eval_before
                    m.eval_after = new_eval_after
                    m.best_move_uci = new_best_move_uci
                    m.best_move_san = new_best_move_san
                    m.best_line = new_best_line
                    m.cp_loss = new_cp_loss

        finally:
            # BUG-04 fix: ensure engine process is always cleaned up
            try:
                await engine.quit()
            except Exception:
                pass
            finally:
                transport.close()

    return result

