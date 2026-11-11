"""Retrieve top knowledge chunks by embedding similarity."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chat.embeddings import EmbeddingClient
from app.models.knowledge_chunk import KnowledgeChunk


@dataclass(frozen=True)
class RetrievedChunk:
    slug: str
    heading: str
    content: str
    source: str

    @property
    def citation(self) -> dict[str, str]:
        url = f"/learn/{self.slug}" if self.source == "learn" else "/learn"
        return {"slug": self.slug, "heading": self.heading, "url": url}


class KnowledgeRetriever:
    """Cosine nearest-neighbor lookup over knowledge_chunks."""

    def __init__(self, session: Session, embedder: EmbeddingClient, *, top_k: int) -> None:
        self._session = session
        self._embedder = embedder
        self._top_k = top_k

    def search(self, query: str) -> list[RetrievedChunk]:
        vector = self._embedder.embed(query)
        distance = KnowledgeChunk.embedding.cosine_distance(vector)
        rows = self._session.scalars(
            select(KnowledgeChunk).order_by(distance).limit(self._top_k)
        ).all()
        return [
            RetrievedChunk(
                slug=row.slug,
                heading=row.heading,
                content=row.content,
                source=row.source,
            )
            for row in rows
        ]
