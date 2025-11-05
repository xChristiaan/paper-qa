"""Minimal citeproc stub used for offline IEEE formatting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, List

from citeproc.source.json import CiteProcJSON


class CitationStylesStyle:
    """Placeholder for citeproc style metadata."""

    def __init__(self, path: str, validate: bool = False) -> None:  # noqa: D401
        self.path = path
        self.validate = validate


@dataclass
class CitationItem:
    key: str
    locator: str | None = None


class Citation:
    """Collection of citation items."""

    def __init__(self, citation_items: Iterable[CitationItem]) -> None:
        self.citation_items = list(citation_items)


@dataclass
class BibliographyEntry:
    key: str
    text: str


class CitationStylesBibliography:
    """Very small bibliography renderer."""

    def __init__(
        self,
        style: CitationStylesStyle,
        source: "CiteProcJSON",
        formatter: Callable[[str], str] | None = None,
    ) -> None:
        self.style = style
        self.source = source
        self.formatter = formatter or (lambda text: text)
        self._order: list[str] = []

    def cite(self, citation: Citation) -> None:
        for item in citation.citation_items:
            if item.key not in self._order:
                self._order.append(item.key)

    def _format_names(self, entry: dict[str, object]) -> str:
        authors = entry.get("author")
        if not isinstance(authors, list):
            return "Unbekannt"
        parts = []
        for author in authors:
            if not isinstance(author, dict):
                continue
            family = author.get("family")
            given = author.get("given")
            literal = author.get("literal")
            if literal:
                parts.append(str(literal))
            else:
                parts_to_join = [
                    str(given) if given else "",
                    str(family) if family else "",
                ]
                label = "".join(filter(None, parts_to_join))
                parts.append(label.strip())
        return " and ".join([part for part in parts if part]) or "Unbekannt"

    def _format_entry(self, entry: dict[str, object]) -> str:
        author = self._format_names(entry)
        title = entry.get("title", "Ohne Titel")
        container = entry.get("container-title") or entry.get("publisher")
        issued = entry.get("issued")
        year = ""
        if isinstance(issued, dict):
            raw = issued.get("raw")
            if isinstance(raw, str):
                year = raw
        components = [f"{author}", f"“{title}”"]
        if container:
            components.append(str(container))
        if year:
            components.append(str(year))
        return ", ".join(components)

    def bibliography(self) -> List[BibliographyEntry]:
        entries: list[BibliographyEntry] = []
        for key in self._order:
            entry = self.source.get_reference(key)
            text = self._format_entry(entry)
            entries.append(BibliographyEntry(key=key, text=self.formatter(text)))
        return entries


__all__ = [
    "BibliographyEntry",
    "Citation",
    "CitationItem",
    "CitationStylesBibliography",
    "CitationStylesStyle",
]
