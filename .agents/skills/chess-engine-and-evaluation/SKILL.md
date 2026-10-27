---
name: chess-engine-and-evaluation
description: Chess domain correctness, Stockfish UCI communication, centipawn perspective conversion, win-probability formulas, and LLM explanation grounding. Essential for all analysis and engine tasks.
license: MIT
---

# Chess Domain Correctness & Stockfish Evaluation Guide

Rules and formulas governing all chess analysis, evaluation, and coaching features in Chessian.AI.

## 1. Evaluation Perspective & Centipawn Loss

Stockfish outputs evaluations in centipawns from **White's perspective**:
- Positive values favor White.
- Negative values favor Black.

### Mover's Perspective Conversion (CRITICAL)
Before calculating move loss, convert the score to the side that made the move:

```python
def to_mover_score(score_cp_white: int, is_white: bool) -> int:
    """Converts a White-centric centipawn score to the mover perspective."""
    return score_cp_white if is_white else -score_cp_white

def compute_centipawn_loss(eval_before: int, eval_after: int, is_white: bool) -> int:
    """
    Computes CPL from the mover perspective.
    eval_before and eval_after are Stockfish scores from White perspective.
    A positive loss means the mover made a sub-optimal move.
    """
    mover_before = to_mover_score(eval_before, is_white)
    mover_after = to_mover_score(eval_after, is_white)
    loss = mover_before - mover_after
    return max(0, loss)
```

---

## 2. Win Probability vs Centipawn Loss

Centipawn loss alone distorts accuracy (e.g. dropping from +1000 to +700 is a 300 CPL drop, but both positions are 99.9% won). Use the win probability formula:

$$W(cp) = \frac{1}{1 + 10^{-cp / 400}} \quad \text{or} \quad W(cp) = \frac{1}{1 + \exp(-0.003682 \times cp)}$$

Win Probability Loss:
$$\Delta W = W(\text{mover\_before}) - W(\text{mover\_after})$$

Move classifications (Best, Inaccuracy, Mistake, Blunder) should prioritize Win Probability loss rather than naive CPL drops.

---

## 3. Depth Consistency Rules

- **Scan Depth**: Fast scan across every position is performed at **depth 14**.
- **Critical Moments Depth**: Critical moments are re-evaluated at **depth 20**.
- **Never compare scores across different depths directly**: Always record and store the `depth` alongside the centipawn score.

---

## 4. Variant Games

- Stockfish configuration only supports standard chess.
- **Skip variant games** (Chess960, King of the Hill, Three-check, Atomic, Horde). Detect and reject them early during import.

---

## 5. Grounded LLM Explanations

When asking the LLM (Groq) to explain a critical moment:
1. Provide the complete board state as FEN and explicit piece coordinates.
2. Provide the played move and the engine's best move with continuation line.
3. System prompt constraint: The LLM must strictly reference pieces present in the FEN and lines provided. Hallucinated pieces or impossible squares are prohibited.
4. If a feature depends on missing data (e.g. `tactical_motifs`), do NOT simulate or mock it. Keep the field null until genuine detector logic exists.
