"""Stockfish engine analysis service."""

import math
from dataclasses import dataclass, field

import chess
import chess.pgn
import chess.engine
import io


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


def classify_move(cp_loss: float) -> str:
    """Classify a move based on centipawn loss."""
    if cp_loss <= 0:
        return "best"
    elif cp_loss < 30:
        return "good"
    elif cp_loss < 50:
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


def _score_to_cp(score: chess.engine.PovScore, color: chess.Color) -> float:
    """Convert engine score to centipawns from white's perspective."""
    pov = score.white()
    if pov.is_mate():
        mate_num = pov.mate()
        if mate_num is None:
            return 0.0
        # Large values for mate scores
        return 10000.0 if mate_num > 0 else -10000.0
    cp = pov.score()
    return float(cp) if cp is not None else 0.0


async def analyze_game(
    pgn_text: str,
    stockfish_path: str = "/usr/bin/stockfish",
    depth: int = 20,
) -> GameEvalResult:
    """
    Analyze a complete game with Stockfish.

    Returns per-move evaluations and aggregate statistics.
    """
    pgn_io = io.StringIO(pgn_text)
    game = chess.pgn.read_game(pgn_io)
    if game is None:
        raise ValueError("Invalid PGN")

    result = GameEvalResult()
    board = game.board()

    transport, engine = await chess.engine.popen_uci(stockfish_path)

    try:
        prev_eval: float = 0.0
        move_number = 0
        white_cp_losses: list[float] = []
        black_cp_losses: list[float] = []

        for node in game.mainline():
            move = node.move
            color = "white" if board.turn == chess.WHITE else "black"
            move_number = board.fullmove_number

            fen_before = board.fen()
            move_san = board.san(move)
            move_uci = move.uci()

            # Get best move and eval BEFORE the move is made
            info_before = await engine.analyse(board, chess.engine.Limit(depth=depth))
            eval_before = _score_to_cp(info_before["score"], board.turn)
            best_move = info_before.get("pv", [None])[0]
            best_move_san = board.san(best_move) if best_move else ""
            best_move_uci = best_move.uci() if best_move else ""
            pv = info_before.get("pv", [])
            best_line = " ".join(m.uci() for m in pv[:5])

            # Make the move
            board.push(move)
            fen_after = board.fen()

            # Get eval AFTER the move
            info_after = await engine.analyse(board, chess.engine.Limit(depth=depth))
            eval_after = _score_to_cp(info_after["score"], board.turn)

            # Compute centipawn loss (from the moving side's perspective)
            if color == "white":
                cp_loss = max(0, eval_before - (-eval_after))
            else:
                cp_loss = max(0, (-eval_before) - eval_after)

            classification = classify_move(cp_loss)

            move_eval = MoveEval(
                move_number=move_number,
                color=color,
                move_uci=move_uci,
                move_san=move_san,
                fen_before=fen_before,
                fen_after=fen_after,
                eval_before=eval_before if color == "white" else -eval_before,
                eval_after=-eval_after if color == "white" else eval_after,
                best_move_uci=best_move_uci,
                best_move_san=best_move_san,
                best_line=best_line,
                cp_loss=cp_loss,
                classification=classification,
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

            prev_eval = eval_after

        # Compute accuracy
        if white_cp_losses:
            white_acpl = sum(white_cp_losses) / len(white_cp_losses)
            result.white_accuracy = compute_accuracy(white_acpl)
        if black_cp_losses:
            black_acpl = sum(black_cp_losses) / len(black_cp_losses)
            result.black_accuracy = compute_accuracy(black_acpl)

        # Mark critical moments (top 5 highest cp_loss moves)
        sorted_moves = sorted(result.moves, key=lambda m: m.cp_loss, reverse=True)
        for m in sorted_moves[:5]:
            if m.cp_loss > 50:
                m.is_critical_moment = True

    finally:
        await engine.quit()

    return result
