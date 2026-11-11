"""Corpus loader chunks Learn articles for ingest."""

from app.chat.corpus_loader import load_corpus_chunks


def test_load_corpus_chunks_includes_learn_and_system_scope():
    chunks = load_corpus_chunks()
    slugs = {chunk.slug for chunk in chunks}
    assert "getting-started" in slugs
    assert "system-scope" in slugs
    assert all(chunk.content.strip() for chunk in chunks)
    assert any(chunk.source == "learn" for chunk in chunks)
    assert any(chunk.source == "system" for chunk in chunks)
