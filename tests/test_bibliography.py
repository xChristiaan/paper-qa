"""Tests for bibliography and citation ordering."""

from __future__ import annotations

import json
from pathlib import Path

from ba_agent.bib import BibliographyManager
from ba_agent.config import Settings


def write_metadata(tmp_path: Path) -> Settings:
    metadata = [
        {
            "id": "doc1",
            "type": "report",
            "title": "Digitale Lernplattformen an Hochschulen",
            "author": [
                {"family": "Müller", "given": "J."},
                {"family": "Schmidt", "given": "P."},
            ],
            "issued": {"raw": "2021"},
            "publisher": "Springer",
        },
        {
            "id": "doc2",
            "type": "article-journal",
            "title": "Adoption von E-Learning-Technologien",
            "author": [{"family": "Klein", "given": "A."}],
            "issued": {"raw": "2022"},
            "container-title": "IEEE Access",
        },
    ]
    data_dir = tmp_path / "data"
    metadata_path = data_dir / "sources.json"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    settings = Settings(
        metadata_file=metadata_path,
        data_dir=data_dir,
        source_dir=tmp_path / "quellen",
        pages_file=data_dir / "pages.jsonl",
        chunk_file=data_dir / "chunks.jsonl",
        index_file=data_dir / "index.faiss",
        embedding_file=data_dir / "embeddings.npz",
    )
    return settings


def test_bibliography_order(tmp_path: Path) -> None:
    settings = write_metadata(tmp_path)
    manager = BibliographyManager(settings)
    first = manager.cite("doc1")
    second = manager.cite("doc2", page=45)
    bibliography = manager.bibliography()
    assert first == "[1]"
    assert second == "[2, p. 45]"
    assert bibliography[0].startswith("[1]")
    assert bibliography[1].startswith("[2]")
