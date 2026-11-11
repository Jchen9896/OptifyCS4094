"""Load and chunk Learn articles plus system scope for ingest."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


@dataclass(frozen=True)
class CorpusChunk:
    source: str
    slug: str
    heading: str
    content: str
    metadata: dict


def load_corpus_chunks() -> list[CorpusChunk]:
    """Return one chunk per Learn section and one for system scope."""
    chunks: list[CorpusChunk] = []
    articles = json.loads((CORPUS_DIR / "learn_articles.json").read_text(encoding="utf-8"))
    for article in articles:
        slug = article["slug"]
        title = article["title"]
        for section in article["sections"]:
            heading = section["heading"]
            body = "\n\n".join(section["paragraphs"])
            content = f"{title}\n\n## {heading}\n\n{body}"
            chunks.append(
                CorpusChunk(
                    source="learn",
                    slug=slug,
                    heading=heading,
                    content=content,
                    metadata={"title": title, "category": article.get("category")},
                )
            )
    scope = (CORPUS_DIR / "system_scope.md").read_text(encoding="utf-8").strip()
    chunks.append(
        CorpusChunk(
            source="system",
            slug="system-scope",
            heading="Optify assistant scope",
            content=scope,
            metadata={"title": "System scope"},
        )
    )
    return chunks
