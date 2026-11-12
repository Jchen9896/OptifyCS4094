"""Risk questionnaire definition and public questionnaire types (Decision 014)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Dimension = Literal["capacity", "willingness"]
ProfileLevelName = Literal[
    "conservative", "moderately_conservative", "moderate", "growth", "aggressive"
]
RecommendedStrategy = Literal["min_variance", "max_sharpe", "target_risk"]


class QuestionOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    points: int = Field(ge=0)


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    dimension: Dimension
    prompt: str = Field(min_length=1)
    options: list[QuestionOption] = Field(min_length=2)

    @model_validator(mode="after")
    def check_options(self) -> "Question":
        ids = [option.id for option in self.options]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Question '{self.id}' has duplicate option ids.")
        # A question where every option scores 0 cannot change the score.
        if max(option.points for option in self.options) == 0:
            raise ValueError(f"Question '{self.id}' needs at least one option with points.")
        return self


class ProfileLevel(BaseModel):
    """One risk level and the optimizer settings it recommends."""

    model_config = ConfigDict(extra="forbid")

    level: ProfileLevelName
    label: str = Field(min_length=1)
    min_score: float = Field(ge=0, le=100)
    description: str = Field(min_length=1)
    strategy: RecommendedStrategy
    max_weight: float = Field(gt=0, le=1)
    target_volatility: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_target(self) -> "ProfileLevel":
        if (self.strategy == "target_risk") != (self.target_volatility is not None):
            raise ValueError(
                f"Level '{self.level}' must set target_volatility only for the target_risk strategy."
            )
        return self


class Questionnaire(BaseModel):
    """The full questionnaire file, with points and profile levels."""

    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=1)
    questions: list[Question] = Field(min_length=1)
    profiles: list[ProfileLevel] = Field(min_length=1)

    @model_validator(mode="after")
    def check_structure(self) -> "Questionnaire":
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)):
            raise ValueError("Question ids must be unique.")
        dimensions = {question.dimension for question in self.questions}
        if dimensions != {"capacity", "willingness"}:
            raise ValueError("Each dimension needs at least one question.")
        levels = [profile.level for profile in self.profiles]
        if len(levels) != len(set(levels)):
            raise ValueError("Profile levels must be unique.")
        scores = [profile.min_score for profile in self.profiles]
        # Every score from 0 to 100 must find exactly one level.
        if scores[0] != 0 or any(low >= high for low, high in zip(scores, scores[1:])):
            raise ValueError("Profile min_score values must start at 0 and increase.")
        return self


class RiskRecommendation(BaseModel):
    """Optimizer settings for a portfolio, and the reasons for them."""

    strategy: RecommendedStrategy
    max_weight: float = Field(gt=0, le=1)
    target_volatility: float | None = None
    # True only when the optimizer ran these settings on the portfolio holdings without a problem.
    checked: bool = False
    notes: list[str] = Field(default_factory=list)


class PublicQuestionOption(BaseModel):
    """An answer option without its points, so the client cannot see the scoring."""

    id: str
    label: str


class PublicQuestion(BaseModel):
    id: str
    prompt: str
    options: list[PublicQuestionOption]


class QuestionnaireResponse(BaseModel):
    version: int
    questions: list[PublicQuestion]

    @classmethod
    def from_questionnaire(cls, questionnaire: Questionnaire) -> "QuestionnaireResponse":
        return cls(
            version=questionnaire.version,
            questions=[
                PublicQuestion(
                    id=question.id,
                    prompt=question.prompt,
                    options=[
                        PublicQuestionOption(id=option.id, label=option.label)
                        for option in question.options
                    ],
                )
                for question in questionnaire.questions
            ],
        )
