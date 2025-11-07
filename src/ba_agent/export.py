"""Export utilities for converting Markdown outputs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from .bib import BibliographyManager
from .config import Settings


class Exporter:
    """Convert Markdown documents and append IEEE bibliography."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.bibliography = BibliographyManager(self.settings)

    def append_bibliography(self, markdown: str, citations: Iterable[str]) -> str:
        bib_entries = list(citations)
        if not bib_entries:
            bib_entries = self.bibliography.bibliography()
        if not bib_entries:
            return markdown
        bibliography = "\n".join(["## Literaturverzeichnis", ""] + list(bib_entries))
        return markdown.rstrip() + "\n\n" + bibliography + "\n"

    def convert(self, markdown_path: Path, output_path: Path) -> None:
        markdown_text = markdown_path.read_text(encoding="utf-8")
        bibliography = self.bibliography.bibliography()
        combined = self.append_bibliography(markdown_text, bibliography)
        temp_path = markdown_path.with_suffix(".tmp.md")
        temp_path.write_text(combined, encoding="utf-8")
        try:
            subprocess.run(
                [
                    "pandoc",
                    str(temp_path),
                    "-o",
                    str(output_path),
                    "--csl",
                    str(self.settings.csl_file),
                ],
                check=True,
            )
        finally:
            temp_path.unlink(missing_ok=True)
