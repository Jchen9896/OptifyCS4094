"""Turn questionnaire answers into a risk score and profile level (Decision 014)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass

from app.core.errors import InvalidRiskAnswersError
from app.schemas.onboarding import Dimension, ProfileLevel, Questionnaire


@dataclass(frozen=True)
class RiskScore:
    """Scores from 0 to 100. `score` is the lower of the two dimension scores."""

    capacity_score: float
    willingness_score: float
    score: float
    profile: ProfileLevel


class RiskScorer(ABC):
    """Calculates a risk score from answers. Answers map question id to option id."""

    @abstractmethod
    def score(self, answers: Mapping[str, str]) -> RiskScore:
        """Return the score. Raise InvalidRiskAnswersError when the answers are not complete or not known."""


class PointsRiskScorer(RiskScorer):
    """Adds the points of the selected options for each dimension."""

    def __init__(self, questionnaire: Questionnaire) -> None:
        self._questionnaire = questionnaire

    def score(self, answers: Mapping[str, str]) -> RiskScore:
        self._validate(answers)
        capacity = self._dimension_score("capacity", answers)
        willingness = self._dimension_score("willingness", answers)
        # Capacity limits willingness: the user gets the lower of the two scores.
        score = min(capacity, willingness)
        return RiskScore(
            capacity_score=capacity,
            willingness_score=willingness,
            score=score,
            profile=self._profile_for(score),
        )

    def _validate(self, answers: Mapping[str, str]) -> None:
        question_ids = {question.id for question in self._questionnaire.questions}
        missing = sorted(question_ids - set(answers))
        if missing:
            raise InvalidRiskAnswersError(f"Answer every question. Missing: {', '.join(missing)}.")
        unknown = sorted(set(answers) - question_ids)
        if unknown:
            raise InvalidRiskAnswersError(f"These questions are not known: {', '.join(unknown)}.")
        for question in self._questionnaire.questions:
            option_ids = {option.id for option in question.options}
            if answers[question.id] not in option_ids:
                raise InvalidRiskAnswersError(
                    f"'{answers[question.id]}' is not an answer for question '{question.id}'."
                )

    def _dimension_score(self, dimension: Dimension, answers: Mapping[str, str]) -> float:
        earned = 0
        possible = 0
        for question in self._questionnaire.questions:
            if question.dimension != dimension:
                continue
            points = {option.id: option.points for option in question.options}
            earned += points[answers[question.id]]
            possible += max(points.values())
        # Multiply before the division, so a score on a level boundary (for example 20) is exact.
        return earned * 100 / possible

    def _profile_for(self, score: float) -> ProfileLevel:
        # The schema makes min_score start at 0 and increase, so the first level always matches.
        matching = [profile for profile in self._questionnaire.profiles if profile.min_score <= score]
        return matching[-1]
