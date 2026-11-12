"""Load the risk questionnaire data file (Decision 014)."""

from __future__ import annotations

from pathlib import Path

from app.schemas.onboarding import Questionnaire

QUESTIONNAIRE_PATH = Path(__file__).resolve().parent / "questionnaire.json"


def load_questionnaire(path: Path = QUESTIONNAIRE_PATH) -> Questionnaire:
    """Read and validate the questionnaire. An invalid file raises a pydantic ValidationError."""
    return Questionnaire.model_validate_json(path.read_text(encoding="utf-8"))
