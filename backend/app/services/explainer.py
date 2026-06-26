"""LLM move explanation service — Groq-backed chess coaching narratives."""

import asyncio
import logging

from groq import Groq

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a concise chess coach. "
    "When given a move, explain in 2-3 plain sentences why it was good or bad "
    "and what the better move achieves. "
    "Never use centipawn numbers or evaluation scores. "
    "Do not use markdown, bullet points, or headers. "
    "Never invent piece locations — only refer to moves by the names given to you. "
    "Speak directly to the player using 'you' and 'your'."
)


def _build_user_prompt(
    move_san: str,
    best_move_san: str,
    cp_loss: float,
    classification: str,
    eval_before: float,
    eval_after: float,
    fen_before: str,
    game_phase: str,
) -> str:
    """Build the user-facing prompt string from move context."""
    # Determine eval swing direction in human terms — no raw numbers exposed
    if classification in ("best", "good", "brilliant"):
        swing = "improved your position"
    elif eval_before > eval_after:
        swing = "made your position significantly worse"
    elif eval_before < eval_after:
        swing = "unexpectedly improved your position"
    else:
        swing = "kept the position roughly equal"

    return (
        f"Game phase: {game_phase}\n"
        f"Position (FEN): {fen_before}\n"
        f"Move played: {move_san} ({classification})\n"
        f"Best move available: {best_move_san}\n"
        f"Effect: this move {swing}.\n\n"
        f"Explain why {move_san} was a {classification} and what {best_move_san} would have accomplished instead."
    )


def _call_groq(
    groq_api_key: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """Synchronous Groq API call — run inside asyncio.to_thread()."""
    client = Groq(api_key=groq_api_key)
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=120,
        temperature=0.4,
    )
    return response.choices[0].message.content or ""


async def explain_move(
    move_san: str,
    best_move_san: str,
    cp_loss: float,
    classification: str,
    eval_before: float,
    eval_after: float,
    fen_before: str,
    game_phase: str,
    groq_api_key: str,
) -> str:
    """
    Generate a natural-language coaching explanation for a chess move.

    Uses Groq's synchronous client inside asyncio.to_thread() to avoid
    blocking the FastAPI event loop during the HTTP call.

    Returns an explanation string, or "" on any error.
    """
    if not groq_api_key:
        logger.warning("explain_move called with empty groq_api_key — skipping")
        return ""

    user_prompt = _build_user_prompt(
        move_san=move_san,
        best_move_san=best_move_san,
        cp_loss=cp_loss,
        classification=classification,
        eval_before=eval_before,
        eval_after=eval_after,
        fen_before=fen_before,
        game_phase=game_phase,
    )

    try:
        explanation = await asyncio.to_thread(
            _call_groq,
            groq_api_key,
            _SYSTEM_PROMPT,
            user_prompt,
        )
        return explanation.strip()
    except Exception as exc:
        logger.error("Groq explain_move failed for move %s: %s", move_san, exc)
        return ""
