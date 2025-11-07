"""Tests for deterministic retrieval behaviour."""

from __future__ import annotations

import json
from pathlib import Path

from ba_agent.config import Settings
from ba_agent.index import IndexBuilder
from ba_agent.query import QueryEngine


def prepare_environment(tmp_path: Path) -> Settings:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = data_dir / "sources.json"
    pages_path = data_dir / "pages.jsonl"
    chunk_path = data_dir / "chunks.jsonl"
    metadata = [
        {
            "id": "doc1",
            "type": "report",
            "title": "KI in der Hochschullehre",
            "author": [{"family": "Beispiel", "given": "A."}],
        }
    ]
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    entry = {
        "doc_id": "doc1",
        "page": 1,
        "text": "Künstliche Intelligenz unterstützt Lernprozesse.",
    }
    pages_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    settings = Settings(
        data_dir=data_dir,
        source_dir=tmp_path / "quellen",
        metadata_file=metadata_path,
        pages_file=pages_path,
        chunk_file=chunk_path,
        index_file=data_dir / "index.faiss",
        embedding_file=data_dir / "embeddings.npz",
    )
    return settings


def test_retrieval_is_deterministic(tmp_path: Path) -> None:
    settings = prepare_environment(tmp_path)
    builder = IndexBuilder(settings)
    builder.build()
    engine = QueryEngine(settings)
    result_first = engine.ask("Welche Rolle spielt KI?")
    result_second = engine.ask("Welche Rolle spielt KI?")
    assert result_first["answer"] == result_second["answer"]
    assert result_first["bibliography"] == result_second["bibliography"]
