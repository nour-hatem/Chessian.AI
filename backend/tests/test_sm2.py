"""Unit tests for the SM-2 spaced-repetition algorithm.

Run with:
    cd backend && python -m pytest tests/test_sm2.py -v

These tests have zero imports from the app layer — sm2.py is a pure module.
"""

import pytest
from datetime import date, timedelta

from app.services.sm2 import SM2State, update_sm2, EASINESS_FLOOR


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

TODAY = date(2026, 6, 27)


def run(state: SM2State, quality: int) -> tuple[SM2State, date]:
    return update_sm2(state, quality, today=TODAY)


# ---------------------------------------------------------------------------
# Basic quality guard
# ---------------------------------------------------------------------------

def test_invalid_quality_raises():
    with pytest.raises(ValueError):
        update_sm2(SM2State(), quality=6)

    with pytest.raises(ValueError):
        update_sm2(SM2State(), quality=-1)


# ---------------------------------------------------------------------------
# First attempt — wrong answer (quality=0)
# ---------------------------------------------------------------------------

def test_first_attempt_wrong_resets_to_tomorrow():
    state = SM2State()
    new_state, due = run(state, quality=0)

    assert new_state.repetitions == 0
    assert new_state.interval == 1
    assert due == TODAY + timedelta(days=1)


def test_wrong_answer_decreases_easiness():
    state = SM2State(easiness=2.5)
    new_state, _ = run(state, quality=0)
    # EF' = 2.5 + (0.1 - 5*0.08 + 5*5*0.02) = 2.5 - 0.8 = 1.7
    assert new_state.easiness < state.easiness


def test_easiness_never_below_floor():
    # Repeatedly answer wrong — easiness must stay >= EASINESS_FLOOR
    state = SM2State(easiness=EASINESS_FLOOR)
    for _ in range(20):
        state, _ = run(state, quality=0)
    assert state.easiness >= EASINESS_FLOOR


# ---------------------------------------------------------------------------
# First attempt — correct (quality=3)
# ---------------------------------------------------------------------------

def test_first_correct_interval_is_1():
    state = SM2State()
    new_state, due = run(state, quality=3)

    assert new_state.repetitions == 1
    assert new_state.interval == 1
    assert due == TODAY + timedelta(days=1)


# ---------------------------------------------------------------------------
# Second correct answer
# ---------------------------------------------------------------------------

def test_second_correct_interval_is_6():
    state = SM2State(repetitions=1, interval=1, easiness=2.5)
    new_state, due = run(state, quality=3)

    assert new_state.repetitions == 2
    assert new_state.interval == 6
    assert due == TODAY + timedelta(days=6)


# ---------------------------------------------------------------------------
# Third correct answer — interval grows by E-factor
# ---------------------------------------------------------------------------

def test_third_correct_interval_grows():
    state = SM2State(repetitions=2, interval=6, easiness=2.5)
    new_state, due = run(state, quality=3)

    # interval = round(6 * easiness_after_q3)
    # EF after q=3: 2.5 + (0.1 - 2*0.08 + 2*2*0.02) = 2.5 + (0.1-0.16+0.08) = 2.5+0.02 = 2.52
    expected_interval = round(6 * new_state.easiness)
    assert new_state.interval == expected_interval
    assert new_state.repetitions == 3
    assert due == TODAY + timedelta(days=expected_interval)


# ---------------------------------------------------------------------------
# Streak reset after a wrong answer mid-sequence
# ---------------------------------------------------------------------------

def test_wrong_after_streak_resets_repetitions():
    state = SM2State(repetitions=5, interval=30, easiness=2.6)
    new_state, due = run(state, quality=0)

    assert new_state.repetitions == 0
    assert new_state.interval == 1
    assert due == TODAY + timedelta(days=1)


# ---------------------------------------------------------------------------
# Perfect answer (quality=5) — easiness increases
# ---------------------------------------------------------------------------

def test_perfect_answer_increases_easiness():
    state = SM2State(easiness=2.5)
    new_state, _ = run(state, quality=5)
    assert new_state.easiness > state.easiness


def test_perfect_sequence_builds_long_interval():
    state = SM2State()
    for _ in range(6):
        state, _ = run(state, quality=5)
    # After 6 perfect answers starting from 0 reps, interval should be > 30 days
    assert state.interval > 30


# ---------------------------------------------------------------------------
# Input immutability — original state must not be mutated
# ---------------------------------------------------------------------------

def test_original_state_not_mutated():
    state = SM2State(easiness=2.5, interval=6, repetitions=2)
    original_easiness = state.easiness
    original_interval = state.interval
    original_reps = state.repetitions

    run(state, quality=3)

    assert state.easiness == original_easiness
    assert state.interval == original_interval
    assert state.repetitions == original_reps


# ---------------------------------------------------------------------------
# Date default (uses today when not passed)
# ---------------------------------------------------------------------------

def test_default_date_is_today():
    state = SM2State()
    _, due = update_sm2(state, quality=3)
    assert due == date.today() + timedelta(days=1)
