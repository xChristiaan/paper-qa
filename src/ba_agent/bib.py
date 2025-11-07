"""Bibliography handling using citeproc-py."""

from __future__ import annotations

import json
from typing import Iterator

from citeproc import (
    Citation,
    CitationItem,
    CitationStylesBibliography,
    CitationStylesStyle,
)
from citeproc.source.json import CiteProcJSON

from .config import CitationLabel, Settings


class BibliographyManager:
    """Assign reference numbers and format IEEE bibliography entries."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self._style = CitationStylesStyle(str(self.settings.csl_file), validate=False)
        self._source = CiteProcJSON(self._load_sources())
        self._bibliography = CitationStylesBibliography(
            self._style, self._source, formatter=lambda text: text
        )
        self._order: dict[str, int] = {}
        self._formatted: dict[int, str] = {}

    def _load_sources(self) -> list[dict[str, object]]:
        if self.settings.metadata_file.exists():
            return json.loads(self.settings.metadata_file.read_text(encoding="utf-8"))
        if self.settings.bib_file.exists():
            return json.loads(self.settings.bib_file.read_text(encoding="utf-8"))
        return []

    def cite(self, source_id: str, page: int | None = None) -> str:
        reference_number = self._order.get(source_id)
        if reference_number is None:
            reference_number = len(self._order) + 1
            self._order[source_id] = reference_number
            citation = Citation([CitationItem(source_id)])
            self._bibliography.cite(citation)
        label = CitationLabel(reference_id=str(reference_number), page=page).label()
        return label

    def bibliography(self) -> list[str]:
        entries: list[str] = []
        bibliography = self._bibliography.bibliography()
        for item in bibliography:
            source_id = item.key
            ref_id = self._order.get(source_id)
            if ref_id is None:
                continue
            text = str(item)
            entries.append(f"[{ref_id}] {text}")
            self._formatted[ref_id] = text
        entries.sort(key=lambda value: int(value.split("]")[0].strip("[")))
        return entries

    def citation_order(self) -> dict[str, int]:
        return dict(self._order)

    def reset(self) -> None:
        self._bibliography = CitationStylesBibliography(
            self._style, self._source, formatter=lambda text: text
        )
        self._order.clear()
        self._formatted.clear()

    def iter_formatted(self) -> Iterator[tuple[int, str]]:
        if not self._formatted:
            self.bibliography()
        for key in sorted(self._formatted):
            yield key, self._formatted[key]
