"""Unit tests for the Curriculum & Improvement Plan service (D1)."""

import uuid
import pytest
from app.services.curriculum import (
    is_task_completed,
    toggle_task_completed,
    weakest_acc_lookup,
    generate_coaching_summary,
)


def test_task_toggle():
    user_id = uuid.uuid4()
    task_id = "task_puzzles_tactics"

    # Initially false
    assert not is_task_completed(user_id, task_id)

    # Toggle to true
    new_state = toggle_task_completed(user_id, task_id)
    assert new_state is True
    assert is_task_completed(user_id, task_id) is True

    # Toggle back to false
    new_state_2 = toggle_task_completed(user_id, task_id)
    assert new_state_2 is False
    assert is_task_completed(user_id, task_id) is False


def test_weakest_acc_lookup():
    assert weakest_acc_lookup("Opening", 40.0, 25.0, 15.0) == 40.0
    assert weakest_acc_lookup("Middlegame", 40.0, 25.0, 15.0) == 25.0
    assert weakest_acc_lookup("Endgame", 40.0, 25.0, 15.0) == 15.0


@pytest.mark.asyncio
async def test_generate_coaching_summary_fallback():
    headline, summary = await generate_coaching_summary(
        username="testuser",
        total_games=50,
        overall_acc=10.0,
        opening_acc=20.0,
        middlegame_acc=8.0,
        endgame_acc=15.0,
        weakest_phase="Middlegame",
        blunder_rate=2.5,
        mistake_rate=4.0,
        trouble_opening="C20 Kings Pawn",
    )
    assert "Middlegame" in headline
    assert "testuser" in summary or "50 analyzed games" in summary or "middlegame" in summary
    assert "C20 Kings Pawn" in summary
