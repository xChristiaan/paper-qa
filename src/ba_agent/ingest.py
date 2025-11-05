"""Document ingestion for the BA-Agent project."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator
from zipfile import ZipFile

import fitz  # type: ignore[import-untyped]

from .config import Settings


def _clean_text(text: str) -> str:
    """Normalize whitespace inside extracted text."""

    return re.sub(r"\s+", " ", text).strip()


@dataclass(slots=True)
class PageRecord:
    """Representation of a page or logical section of a document."""

    doc_id: str
    page: int
    text: str
    source_path: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentMetadata:
    """Metadata container that can be serialized to CSL JSON."""

    doc_id: str
    title: str
    authors: list[str]
    issued: str | None = None
    doi: str | None = None
    publisher: str | None = None

    def to_csl_json(self) -> dict[str, object]:
        """Return a citeproc compatible JSON record."""

        author_list = []
        for author in self.authors:
            parts = author.split()
            if not parts:
                continue
            family = parts[-1]
            given = " ".join(parts[:-1]) if len(parts) > 1 else ""
            author_list.append({"family": family, "given": given})
        data: dict[str, object] = {
            "id": self.doc_id,
            "type": "report",
            "title": self.title,
            "author": author_list or [{"literal": "Unbekannt"}],
        }
        if self.issued:
            data["issued"] = {"raw": self.issued}
        if self.doi:
            data["DOI"] = self.doi
        if self.publisher:
            data["publisher"] = self.publisher
        return data


class DocumentIngestor:
    """Read source documents and prepare them for indexing."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.settings.ensure_directories()

    def _iter_sources(self, source_dir: Path | None = None) -> Iterator[Path]:
        src_dir = source_dir or self.settings.source_dir
        for path in sorted(src_dir.glob("**/*")):
            if path.suffix.lower() in {".pdf", ".txt", ".docx"} and path.is_file():
                yield path

    def _load_docx(self, path: Path) -> list[str]:
        """Extract text from a DOCX file using the OpenXML structure."""

        paragraphs: list[str] = []
        with ZipFile(path) as archive:
            xml_bytes = archive.read("word/document.xml")
        root = ET.fromstring(xml_bytes)
        namespace = {
            "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        }
        for para in root.findall(".//w:p", namespace):
            texts = [
                node.text
                for node in para.findall(".//w:t", namespace)
                if node.text
            ]
            if texts:
                paragraphs.append(_clean_text(" ".join(texts)))
        return paragraphs

    def _iter_pdf_pages(
        self, path: Path, ocr: bool = False
    ) -> Iterator[tuple[int, str, dict[str, str]]]:
        doc = fitz.open(path)
        metadata = doc.metadata or {}
        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if not text and ocr:
                text = page.get_text("text", flags=fitz.TEXT_PRESERVE_IMAGES)
            yield page_index, _clean_text(text), {
                "title": metadata.get("title") or path.stem,
                "author": metadata.get("author")
                or metadata.get("creator")
                or "Unbekannt",
                "creationDate": metadata.get("creationDate") or "",
                "doi": metadata.get("doi") or metadata.get("DOI") or "",
                "producer": metadata.get("producer") or "",
            }

    def ingest(
        self, source_dir: Path | None = None, ocr: bool = False
    ) -> list[PageRecord]:
        """Ingest the configured source documents."""

        records: list[PageRecord] = []
        metadata_map: dict[str, DocumentMetadata] = {}
        for path in self._iter_sources(source_dir):
            doc_id = path.stem
            if path.suffix.lower() == ".pdf":
                for page, text, metadata in self._iter_pdf_pages(path, ocr=ocr):
                    if not text:
                        continue
                    doc_meta = metadata_map.setdefault(
                        doc_id,
                        DocumentMetadata(
                            doc_id=doc_id,
                            title=metadata.get("title") or path.stem,
                            authors=[metadata.get("author") or "Unbekannt"],
                            issued=metadata.get("creationDate") or None,
                            doi=metadata.get("doi") or None,
                            publisher=metadata.get("producer") or None,
                        ),
                    )
                    records.append(
                        PageRecord(
                            doc_id=doc_id,
                            page=page,
                            text=text,
                            source_path=str(path),
                            metadata=doc_meta.to_csl_json(),
                        )
                    )
            elif path.suffix.lower() == ".txt":
                text = path.read_text(encoding="utf-8")
                cleaned = _clean_text(text)
                if cleaned:
                    doc_meta = metadata_map.setdefault(
                        doc_id,
                        DocumentMetadata(
                            doc_id=doc_id,
                            title=path.stem,
                            authors=["Unbekannt"],
                        ),
                    )
                    records.append(
                        PageRecord(
                            doc_id=doc_id,
                            page=1,
                            text=cleaned,
                            source_path=str(path),
                            metadata=doc_meta.to_csl_json(),
                        )
                    )
            elif path.suffix.lower() == ".docx":
                paragraphs = self._load_docx(path)
                if not paragraphs:
                    continue
                doc_meta = metadata_map.setdefault(
                    doc_id,
                    DocumentMetadata(
                        doc_id=doc_id, title=path.stem, authors=["Unbekannt"]
                    ),
                )
                for idx, para in enumerate(paragraphs, start=1):
                    records.append(
                        PageRecord(
                            doc_id=doc_id,
                            page=idx,
                            text=para,
                            source_path=str(path),
                            metadata=doc_meta.to_csl_json(),
                        )
                    )
        self._write_outputs(records, metadata_map)
        return records

    def _write_outputs(
        self, records: Iterable[PageRecord], metadata_map: dict[str, DocumentMetadata]
    ) -> None:
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        with self.settings.pages_file.open("w", encoding="utf-8") as fh:
            for record in records:
                fh.write(
                    json.dumps(
                        {
                            "doc_id": record.doc_id,
                            "page": record.page,
                            "text": record.text,
                            "source_path": record.source_path,
                        }
                    )
                    + "\n"
                )
        sources = [meta.to_csl_json() for meta in metadata_map.values()]
        self.settings.metadata_file.write_text(
            json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8"
        )
