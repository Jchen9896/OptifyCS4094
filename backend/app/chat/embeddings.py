"""Gemini embedding client for knowledge ingest and retrieval."""

from google import genai

from app.core.config import Settings


class EmbeddingClient:
    """Create embedding vectors with the configured Gemini model."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for embeddings.")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embed_model
        self._dimensions = settings.chat_embedding_dimensions

    def embed(self, text: str) -> list[float]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=text,
            config={"output_dimensionality": self._dimensions},
        )
        values = result.embeddings[0].values
        return [float(value) for value in values]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]
