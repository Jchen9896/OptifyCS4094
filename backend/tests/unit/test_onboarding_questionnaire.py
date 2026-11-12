"""Risk questionnaire file and schema rules (Decision 014)."""

import pytest
from pydantic import ValidationError

from app.onboarding.questionnaire_loader import load_questionnaire
from app.schemas.onboarding import Questionnaire, QuestionnaireResponse


def _valid_data() -> dict:
    option_set = [
        {"id": "low", "label": "Low", "points": 0},
        {"id": "high", "label": "High", "points": 2},
    ]
    return {
        "version": 1,
        "questions": [
            {"id": "horizon", "dimension": "capacity", "prompt": "When?", "options": option_set},
            {"id": "reaction", "dimension": "willingness", "prompt": "What?", "options": option_set},
        ],
        "profiles": [
            {
                "level": "conservative", "label": "Conservative", "min_score": 0,
                "description": "Low.", "strategy": "min_variance", "max_weight": 0.25,
                "target_volatility": None,
            },
            {
                "level": "moderate", "label": "Moderate", "min_score": 50,
                "description": "Mid.", "strategy": "target_risk", "max_weight": 0.35,
                "target_volatility": 0.12,
            },
        ],
    }


def test_shipped_questionnaire_is_valid_and_has_five_levels():
    questionnaire = load_questionnaire()
    assert [profile.level for profile in questionnaire.profiles] == [
        "conservative", "moderately_conservative", "moderate", "growth", "aggressive",
    ]
    assert {question.dimension for question in questionnaire.questions} == {"capacity", "willingness"}


def test_shipped_questionnaire_does_not_recommend_target_return():
    questionnaire = load_questionnaire()
    assert all(profile.strategy != "target_return" for profile in questionnaire.profiles)


def test_valid_data_passes():
    assert Questionnaire.model_validate(_valid_data()).version == 1


def test_duplicate_question_ids_fail():
    data = _valid_data()
    data["questions"][1]["id"] = "horizon"
    with pytest.raises(ValidationError, match="Question ids must be unique"):
        Questionnaire.model_validate(data)


def test_duplicate_option_ids_fail():
    data = _valid_data()
    data["questions"][0]["options"] = [
        {"id": "same", "label": "A", "points": 0},
        {"id": "same", "label": "B", "points": 1},
    ]
    with pytest.raises(ValidationError, match="duplicate option ids"):
        Questionnaire.model_validate(data)


def test_question_with_only_zero_points_fails():
    data = _valid_data()
    data["questions"][0]["options"] = [
        {"id": "a", "label": "A", "points": 0},
        {"id": "b", "label": "B", "points": 0},
    ]
    with pytest.raises(ValidationError, match="at least one option with points"):
        Questionnaire.model_validate(data)


def test_missing_dimension_fails():
    data = _valid_data()
    data["questions"][1]["dimension"] = "capacity"
    with pytest.raises(ValidationError, match="Each dimension"):
        Questionnaire.model_validate(data)


@pytest.mark.parametrize("scores", [[10, 50], [0, 0], [50, 0]])
def test_min_scores_must_start_at_zero_and_increase(scores):
    data = _valid_data()
    data["profiles"][1]["level"] = "growth"
    for profile, score in zip(data["profiles"], scores):
        profile["min_score"] = score
    with pytest.raises(ValidationError, match="must start at 0 and increase"):
        Questionnaire.model_validate(data)


@pytest.mark.parametrize(
    ("strategy", "target"), [("target_risk", None), ("min_variance", 0.1), ("max_sharpe", 0.1)]
)
def test_target_volatility_only_with_target_risk(strategy, target):
    data = _valid_data()
    data["profiles"][1]["strategy"] = strategy
    data["profiles"][1]["target_volatility"] = target
    with pytest.raises(ValidationError, match="target_volatility only for the target_risk"):
        Questionnaire.model_validate(data)


def test_target_return_strategy_is_rejected():
    data = _valid_data()
    data["profiles"][0]["strategy"] = "target_return"
    with pytest.raises(ValidationError):
        Questionnaire.model_validate(data)


def test_public_response_hides_points():
    response = QuestionnaireResponse.from_questionnaire(Questionnaire.model_validate(_valid_data()))
    payload = response.model_dump()
    assert payload["version"] == 1
    assert [question["id"] for question in payload["questions"]] == ["horizon", "reaction"]
    assert "points" not in payload["questions"][0]["options"][0]
    assert "dimension" not in payload["questions"][0]
