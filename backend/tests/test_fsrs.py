from datetime import datetime, timezone

from study.fsrs import ReviewState, review

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _new_card() -> ReviewState:
    return ReviewState(stability=0.0, difficulty=0.0, review_count=0)


def test_new_card_reviewed_again_has_a_short_next_interval():
    result = review(_new_card(), "again", now=NOW)

    interval = (result.due_date - NOW).days
    assert interval <= 1


def test_new_card_reviewed_easy_has_a_longer_next_interval_than_again():
    again_result = review(_new_card(), "again", now=NOW)
    easy_result = review(_new_card(), "easy", now=NOW)

    again_interval = (again_result.due_date - NOW).days
    easy_interval = (easy_result.due_date - NOW).days

    assert easy_interval > again_interval


def test_repeated_good_reviews_generally_increase_stability():
    state = _new_card()
    now = NOW

    result = review(state, "good", now=now)
    stabilities = [result.stability]
    state = ReviewState(result.stability, result.difficulty, result.review_count)
    last_reviewed_at = now

    for _ in range(5):
        now = result.due_date  # simulate reviewing exactly when the card comes due
        result = review(state, "good", now=now, last_reviewed_at=last_reviewed_at)
        stabilities.append(result.stability)
        state = ReviewState(result.stability, result.difficulty, result.review_count)
        last_reviewed_at = now

    assert stabilities == sorted(stabilities)
    assert stabilities[-1] > stabilities[0]
