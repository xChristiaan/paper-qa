"""Smoke tests for the BA-Agent CLI."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ba_agent import cli

RUNNER = CliRunner()


def build_env(base_dir: Path) -> dict[str, str]:
    data_dir = base_dir / "data"
    metadata_dir = base_dir / "metadata"
    quellen_dir = base_dir / "quellen"
    data_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    quellen_dir.mkdir(parents=True, exist_ok=True)
    ieee_source = Path("metadata/ieee.csl")
    (metadata_dir / "ieee.csl").write_text(
        ieee_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (metadata_dir / "zotero.csl.json").write_text("[]", encoding="utf-8")
    env = {
        "DATA_DIR": str(data_dir),
        "SOURCE_DIR": str(quellen_dir),
        "PAGES_FILE": str(data_dir / "pages.jsonl"),
        "CHUNK_FILE": str(data_dir / "chunks.jsonl"),
        "INDEX_FILE": str(data_dir / "index.faiss"),
        "EMBEDDING_FILE": str(data_dir / "embeddings.npz"),
        "METADATA_FILE": str(data_dir / "sources.json"),
        "BIB_FILE": str(metadata_dir / "zotero.csl.json"),
        "CSL_FILE": str(metadata_dir / "ieee.csl"),
    }
    return env


def test_cli_commands(tmp_path: Path, monkeypatch) -> None:
    env = build_env(tmp_path)
    source_dir = Path(env["SOURCE_DIR"])
    sample = source_dir / "sample.txt"
    sample.write_text(
        "Künstliche Intelligenz verändert die Hochschullehre nachhaltig.",
        encoding="utf-8",
    )

    result_ingest = RUNNER.invoke(
        cli.app, ["ingest", "--src", str(source_dir)], env=env
    )
    assert result_ingest.exit_code == 0

    result_index = RUNNER.invoke(cli.app, ["index"], env=env)
    assert result_index.exit_code == 0

    result_ask = RUNNER.invoke(cli.app, ["ask", "--q", "Wie wirkt KI?"], env=env)
    assert result_ask.exit_code == 0
    assert "[1]" in result_ask.stdout

    result_chapter = RUNNER.invoke(
        cli.app,
        ["chapter", "--title", "Einführung", "--topic", "KI"],
        env=env,
    )
    assert result_chapter.exit_code == 0

    review_file = tmp_path / "draft.md"
    review_file.write_text("KI wirkt transformativ. [1]\n", encoding="utf-8")
    env_with_file = dict(env)
    result_review = RUNNER.invoke(
        cli.app, ["review", "--in", str(review_file)], env=env_with_file
    )
    assert result_review.exit_code == 0
    data = json.loads(result_review.stdout)
    assert "warnings" in data

    def fake_convert(markdown: Path, output: Path) -> None:
        output.write_bytes(b"ok")

    monkeypatch.setattr(
        "ba_agent.export.Exporter.convert",
        lambda self, markdown, output: fake_convert(markdown, output),
    )
    markdown_path = tmp_path / "doc.md"
    markdown_path.write_text("Inhalt. [1]\n", encoding="utf-8")
    output_path = tmp_path / "doc.docx"
    result_export = RUNNER.invoke(
        cli.app, ["export", str(markdown_path), str(output_path)], env=env
    )
    assert result_export.exit_code == 0
    assert output_path.exists()
