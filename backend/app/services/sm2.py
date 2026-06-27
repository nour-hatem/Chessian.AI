"""
SM-2 spaced-repetition algorithm — pure, stateless, unit-testable.

Reference: Piotr Wozniak's original SM-2 algorithm (1987).
https://www.supermemo.com/en/blog/application-of-a-computer-to-improve-the-results-obtained-in-working-with-the-supermemo-method

Quality scale (used throughout Chessian puzzles):
    0 — completely wrong / gave up
    3 — correct but required hint or significant effort
    5 — correct immediately, confident

The caller maps UI outcomes to quality:
    wrong answer  → quality = 0
    correct       → quality = 3
    correct fast  → quality = 5  (optional; UI can always use 3 for correct)
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SM2State:
    """Mutable SM-2 state for one (user, puzzle) pair."""
    easiness: float = 2.5    # E-factor; never drops below EASINESS_FLOOR
    interval: int = 1        # days until next scheduled review
    repetitions: int = 0     # consecutive correct answers


EASINESS_FLOOR: float = 1.3


def update_sm2(state: SM2State, quality: int, today: date | None = None) -> tuple[SM2State, date]:
    """
    Apply one SM-2 review and return (new_state, next_due_date).

    Args:
        state:    Current SM-2 state for this (user, puzzle) pair.
        quality:  Response quality integer 0-5.
        today:    Date of the review (defaults to date.today()).

    Returns:
        A new SM2State (original is not mutated) and the next due date.

    Algorithm:
        If quality < 3 (incorrect):
            - Reset repetitions to 0.
            - Reset interval to 1 day (review tomorrow).
            - E-factor is still updated (can decrease on failure).
        If quality >= 3 (correct):
            - interval[0] = 1
            - interval[1] = 6
            - interval[n] = round(interval[n-1] * easiness)
            - repetitions += 1
        E-factor update (applied regardless of correctness):
            EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
            EF' = max(EASINESS_FLOOR, EF')
    """
    if quality < 0 or quality > 5:
        raise ValueError(f"SM-2 quality must be 0-5, got {quality!r}")

    if today is None:
        today = date.today()

    # Copy state — never mutate the input
    new_easiness = state.easiness
    new_interval = state.interval
    new_repetitions = state.repetitions

    # Update E-factor (applies even on failure — can decrease)
    new_easiness = new_easiness + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_easiness = max(EASINESS_FLOOR, new_easiness)

    if quality < 3:
        # Incorrect — reset streak, review again tomorrow
        new_repetitions = 0
        new_interval = 1
    else:
        # Correct — advance interval
        if new_repetitions == 0:
            new_interval = 1
        elif new_repetitions == 1:
            new_interval = 6
        else:
            new_interval = round(new_interval * new_easiness)
        new_repetitions += 1

    next_due = today + timedelta(days=new_interval)
    new_state = SM2State(
        easiness=round(new_easiness, 4),
        interval=new_interval,
        repetitions=new_repetitions,
    )
    return new_state, next_due
