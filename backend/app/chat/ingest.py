"""Embed corpus chunks into knowledge_chunks. Run: python -m app.chat.ingest"""

from __future__ import annotations

from sqlalchemy import delete

from app.chat.corpus_loader import load_corpus_chunks
from app.chat.embeddings import EmbeddingClient
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models.knowledge_chunk import KnowledgeChunk


def ingest_knowledge(*, replace: bool = True) -> int:
    """Upsert Learn + system chunks. Returns the number of chunks written."""
    settings = get_settings()
    embedder = EmbeddingClient(settings)
    chunks = load_corpus_chunks()
    vectors = embedder.embed_many([chunk.content for chunk in chunks])
    with SessionLocal() as session:
        if replace:
            session.execute(delete(KnowledgeChunk))
        for chunk, vector in zip(chunks, vectors):
            session.add(
                KnowledgeChunk(
                    source=chunk.source,
                    slug=chunk.slug,
                    heading=chunk.heading,
                    content=chunk.content,
                    embedding=vector,
                    chunk_metadata=chunk.metadata,
                )
            )
        session.commit()
    return len(chunks)


def main() -> None:
    count = ingest_knowledge()
    print(f"Ingested {count} knowledge chunks.")


if __name__ == "__main__":
    main()
