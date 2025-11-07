"""Typer CLI for BA-Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from .config import Settings
from .export import Exporter
from .index import IndexBuilder
from .ingest import DocumentIngestor
from .query import QueryEngine
from .review import review_file

app = typer.Typer(help="BA-Agent CLI für IEEE-konforme wissenschaftliche Texte")


def _settings_from_env(source_dir: Optional[Path]) -> Settings:
    settings = Settings()
    if source_dir is not None:
        settings.source_dir = source_dir
    settings.ensure_directories()
    return settings


@app.command()
def ingest(
    src: Path = typer.Option(Path("./quellen"), "--src", help="Pfad zu den Quellen")
) -> None:
    """Ingest source documents into the local store."""

    settings = _settings_from_env(src)
    ingestor = DocumentIngestor(settings)
    records = ingestor.ingest(source_dir=src)
    typer.echo(f"Ingestion abgeschlossen: {len(records)} Einträge gespeichert.")


@app.command()
def index() -> None:
    """Build the FAISS index for the ingested documents."""

    settings = Settings()
    builder = IndexBuilder(settings)
    try:
        chunks = builder.build()
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error
    typer.echo(f"Index erstellt mit {len(chunks)} Chunks.")


@app.command()
def ask(q: str = typer.Option(..., "--q", help="Fragestellung")) -> None:
    """Answer a question using RAG over the local sources."""

    settings = Settings()
    try:
        engine = QueryEngine(settings)
        result = engine.ask(q)
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error
    typer.echo(result["answer"])
    typer.echo("\nLiteraturverzeichnis:")
    for entry in result["bibliography"]:
        typer.echo(entry)


@app.command()
def chapter(
    title: str = typer.Option(..., "--title", help="Kapitelüberschrift"),
    topic: str = typer.Option(..., "--topic", help="Kapitelthema"),
) -> None:
    """Generate a chapter outline."""

    settings = Settings()
    try:
        engine = QueryEngine(settings)
        result = engine.chapter(title, topic)
    except FileNotFoundError as error:
        typer.echo(str(error))
        raise typer.Exit(code=1) from error
    typer.echo(result["text"])
    typer.echo("\nLiteraturverzeichnis:")
    for entry in result["bibliography"]:
        typer.echo(entry)


@app.command()
def review(
    input_path: Path = typer.Option(..., "--in", help="Pfad zum Markdown-Entwurf")
) -> None:
    """Review a markdown document for IEEE compliance."""

    warnings = review_file(input_path)
    typer.echo(json.dumps(warnings, ensure_ascii=False, indent=2))


@app.command()
def export(markdown: Path, output: Path) -> None:
    """Convert a markdown file to DOCX or LaTeX with bibliography."""

    settings = Settings()
    exporter = Exporter(settings)
    exporter.convert(markdown, output)
    typer.echo(f"Export abgeschlossen: {output}")


def run() -> None:
    app()


if __name__ == "__main__":  # pragma: no cover
    run()
