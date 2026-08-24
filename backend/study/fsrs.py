"""Clean-room implementation of the FSRS v4 (Free Spaced Repetition Scheduler) update.

Pure functions only: given a card's current review state and a grade, compute
its new state. No datetime.now(), no DB, no I/O. The caller (study/scheduler.py)
is responsible for reading state from and writing state to storage, and for
supplying "now" explicitly so results stay deterministic and testable.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

Grade = Literal["again", "hard", "good", "easy"]

_GRADE_VALUES: dict[Grade, int] = {"again": 1, "hard": 2, "good": 3, "easy": 4}

# FSRS v4 default parameter weights (w0..w16), as published by the
# open-spaced-repetition project. Indices below follow that numbering.
DEFAULT_WEIGHTS: tuple[float, ...] = (
    0.4, 0.6, 2.4, 5.8, 4.93, 0.94, 0.86, 0.01, 1.49, 0.14,
    0.94, 2.18, 0.05, 0.34, 1.26, 0.29, 2.61,
)

DEFAULT_REQUESTED_RETENTION = 0.9
MIN_STABILITY = 0.1
MIN_DIFFICULTY = 1.0
MAX_DIFFICULTY = 10.0


@dataclass(frozen=True)
class ReviewState:
    stability: float
    difficulty: float
    review_count: int


@dataclass(frozen=True)
class ReviewResult:
    stability: float
    difficulty: float
    due_date: datetime
    review_count: int


def _clamp_difficulty(difficulty: float) -> float:
    return min(MAX_DIFFICULTY, max(MIN_DIFFICULTY, difficulty))


def _initial_stability(grade: Grade, weights: tuple[float, ...]) -> float:
    return weights[_GRADE_VALUES[grade] - 1]


def _initial_difficulty(grade: Grade, weights: tuple[float, ...]) -> float:
    g = _GRADE_VALUES[grade]
    return _clamp_difficulty(weights[4] - (g - 3) * weights[5])


def _retrievability(elapsed_days: float, stability: float) -> float:
    return (1 + elapsed_days / (9 * stability)) ** -1


def _next_difficulty(difficulty: float, grade: Grade, weights: tuple[float, ...]) -> float:
    g = _GRADE_VALUES[grade]
    # Mean-reverts toward D0(3) (== w4, since (3-3)*w5 == 0) so a single bad
    # review doesn't permanently inflate difficulty ("ease hell").
    good_default = weights[4]
    reverted = weights[7] * good_default + (1 - weights[7]) * (difficulty - weights[6] * (g - 3))
    return _clamp_difficulty(reverted)


def _next_stability_success(
    stability: float, difficulty: float, retrievability: float, grade: Grade, weights: tuple[float, ...]
) -> float:
    if grade == "hard":
        multiplier = weights[15]
    elif grade == "easy":
        multiplier = weights[16]
    else:
        multiplier = 1.0
    exponent = (
        weights[8]
        * (11 - difficulty)
        * stability ** (-weights[9])
        * (math.exp(weights[10] * (1 - retrievability)) - 1)
        * multiplier
    )
    return stability * (math.exp(exponent) + 1)


def _next_stability_failure(
    stability: float, difficulty: float, retrievability: float, weights: tuple[float, ...]
) -> float:
    return (
        weights[11]
        * difficulty ** (-weights[12])
        * ((stability + 1) ** weights[13] - 1)
        * math.exp(weights[14] * (1 - retrievability))
    )


def _interval_days(stability: float, requested_retention: float) -> float:
    return 9 * stability * (1 / requested_retention - 1)


def review(
    state: ReviewState,
    grade: Grade,
    now: datetime,
    last_reviewed_at: datetime | None = None,
    requested_retention: float = DEFAULT_REQUESTED_RETENTION,
    weights: tuple[float, ...] = DEFAULT_WEIGHTS,
) -> ReviewResult:
    """Compute the next review state for a card given a grade.

    `state.review_count == 0` is treated as the card's first-ever review,
    which FSRS scores with separate initial-stability/difficulty formulas
    rather than the update formulas (there's no prior retrievability to
    react to). For any later review, `last_reviewed_at` is required so
    elapsed time (and therefore retrievability) can be computed.
    """
    if state.review_count == 0:
        stability = _initial_stability(grade, weights)
        difficulty = _initial_difficulty(grade, weights)
    else:
        if last_reviewed_at is None:
            raise ValueError("last_reviewed_at is required for a card that has been reviewed before")
        elapsed_days = max(0.0, (now - last_reviewed_at).total_seconds() / 86400)
        retrievability = _retrievability(elapsed_days, state.stability)
        difficulty = _next_difficulty(state.difficulty, grade, weights)
        if grade == "again":
            stability = _next_stability_failure(state.stability, state.difficulty, retrievability, weights)
        else:
            stability = _next_stability_success(state.stability, state.difficulty, retrievability, grade, weights)
        stability = max(MIN_STABILITY, stability)

    # Interval is rounded to whole days with a 1-day floor; FSRS v5's
    # same-day re-review formula (sub-day intervals) is deliberately not
    # implemented here — see module docstring.
    interval_days = max(1, round(_interval_days(stability, requested_retention)))
    due_date = now + timedelta(days=interval_days)

    return ReviewResult(
        stability=stability,
        difficulty=difficulty,
        due_date=due_date,
        review_count=state.review_count + 1,
    )
