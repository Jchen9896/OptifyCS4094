"""Points scorer for the risk questionnaire (Decision 014)."""

import pytest

from app.core.errors import InvalidRiskAnswersError
from app.onboarding.questionnaire_loader import load_questionnaire
from app.onboarding.scoring import PointsRiskScorer
from app.schemas.onboarding import Questionnaire


def _option(option_id: str, points: int) -> dict:
    return {"id": option_id, "label": option_id, "points": points}


def _profile(level: str, min_score: float) -> dict:
    return {
        "level": level, "label": level, "min_score": min_score, "description": level,
        "strategy": "min_variance", "max_weight": 0.5, "target_volatility": None,
    }


# Each dimension has 5 possible points, so 1 point is exactly 20.
SMALL = Questionnaire.model_validate({
    "version": 1,
    "questions": [
        {"id": "cap1", "dimension": "capacity", "prompt": "?",
         "options": [_option("a", 0), _option("b", 1), _option("c", 2)]},
        {"id": "cap2", "dimension": "capacity", "prompt": "?",
         "options": [_option("a", 0), _option("b", 3)]},
        {"id": "will1", "dimension": "willingness", "prompt": "?",
         "options": [_option("a", 0), _option("b", 1), _option("c", 4)]},
        {"id": "will2", "dimension": "willingness", "prompt": "?",
         "options": [_option("a", 0), _option("b", 1)]},
    ],
    "profiles": [
        _profile("conservative", 0), _profile("moderate", 20),
        _profile("growth", 60), _profile("aggressive", 80),
    ],
})


@pytest.mark.parametrize(
    ("answers", "capacity", "willingness", "level"),
    [
        ({"cap1": "a", "cap2": "a", "will1": "a", "will2": "a"}, 0, 0, "conservative"),
        # Exactly on the min_score boundary selects the higher level.
        ({"cap1": "b", "cap2": "a", "will1": "b", "will2": "a"}, 20, 20, "moderate"),
        ({"cap1": "c", "cap2": "b", "will1": "c", "will2": "a"}, 100, 80, "aggressive"),
        ({"cap1": "c", "cap2": "b", "will1": "c", "will2": "b"}, 100, 100, "aggressive"),
        # The lower dimension sets the level.
        ({"cap1": "c", "cap2": "b", "will1": "a", "will2": "a"}, 100, 0, "conservative"),
        ({"cap1": "c", "cap2": "a", "will1": "c", "will2": "b"}, 40, 100, "moderate"),
    ],
)
def test_scores_and_level(answers, capacity, willingness, level):
    result = PointsRiskScorer(SMALL).score(answers)
    assert result.capacity_score == capacity
    assert result.willingness_score == willingness
    assert result.score == min(capacity, willingness)
    assert result.profile.level == level


@pytest.mark.parametrize(
    ("answers", "message"),
    [
        ({"cap1": "a", "cap2": "a", "will1": "a"}, "Missing: will2"),
        ({"cap1": "a", "cap2": "a", "will1": "a", "will2": "a", "extra": "a"}, "not known: extra"),
        ({"cap1": "z", "cap2": "a", "will1": "a", "will2": "a"}, "'z' is not an answer for question 'cap1'"),
    ],
)
def test_invalid_answers_raise(answers, message):
    with pytest.raises(InvalidRiskAnswersError, match=message) as caught:
        PointsRiskScorer(SMALL).score(answers)
    assert caught.value.status_code == 422
    assert caught.value.code == "invalid_risk_answers"


def _shipped_answers(pick) -> dict[str, str]:
    questionnaire = load_questionnaire()
    return {question.id: pick(question.options).id for question in questionnaire.questions}


def test_shipped_lowest_answers_are_conservative():
    answers = _shipped_answers(lambda options: min(options, key=lambda option: option.points))
    assert PointsRiskScorer(load_questionnaire()).score(answers).profile.level == "conservative"


def test_shipped_highest_answers_are_aggressive():
    answers = _shipped_answers(lambda options: max(options, key=lambda option: option.points))
    assert PointsRiskScorer(load_questionnaire()).score(answers).profile.level == "aggressive"


def test_shipped_long_horizon_with_low_willingness_stays_conservative():
    questionnaire = load_questionnaire()
    answers = {
        question.id: (
            max(question.options, key=lambda option: option.points)
            if question.dimension == "capacity"
            else min(question.options, key=lambda option: option.points)
        ).id
        for question in questionnaire.questions
    }
    result = PointsRiskScorer(questionnaire).score(answers)
    assert result.capacity_score == 100
    assert result.profile.level == "conservative"
