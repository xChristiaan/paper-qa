"""Query pipeline implementing retrieval-augmented generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .bib import BibliographyManager
from .config import Settings
from .index import EmbeddingBackend, load_embeddings

try:  # pragma: no cover - optional dependency
    import faiss  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    faiss = None


@dataclass(slots=True)
class RetrievedChunk:
    doc_id: str
    page: int
    text: str
    score: float


class QueryEngine:
    """RAG pipeline restricted to the local index."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.bibliography = BibliographyManager(self.settings)
        self.backend = EmbeddingBackend(
            self.settings.embedding_model, self.settings.random_seed
        )
        self.index, self.chunks = load_embeddings(self.settings)

    def _search(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        k = top_k or self.settings.top_k
        query_vec = self.backend.encode([query])[0]
        if faiss is not None and hasattr(self.index, "search"):
            distances, indices = self.index.search(np.asarray([query_vec]), k)
            scores = distances[0]
            positions = indices[0]
        else:  # pragma: no cover - fallback path for npz storage
            embeddings = np.asarray(self.index, dtype="float32")
            scores = embeddings @ query_vec
            positions = np.argsort(scores)[::-1][:k]
            scores = scores[positions]
        retrieved: list[RetrievedChunk] = []
        for score, pos in zip(scores, positions):
            if pos < 0 or pos >= len(self.chunks):
                continue
            chunk = self.chunks[pos]
            retrieved.append(
                RetrievedChunk(
                    doc_id=chunk["doc_id"],
                    page=int(chunk["page"]),
                    text=chunk["text"],
                    score=float(score),
                )
            )
        return retrieved

    def _make_sentence(self, chunk: RetrievedChunk) -> str:
        sentences = [part.strip() for part in chunk.text.split(".") if part.strip()]
        snippet = sentences[0] if sentences else chunk.text[:200]
        citation = self.bibliography.cite(chunk.doc_id, page=chunk.page)
        return f"{snippet}. {citation}"

    def _compose_answer(self, question: str, results: list[RetrievedChunk]) -> str:
        if not results:
            return "Es wurden keine passenden Quellen gefunden."
        intro = f"Analyse der Frage: {question}."
        body_sentences = [self._make_sentence(chunk) for chunk in results]
        conclusion = (
            "Die Bewertung basiert ausschließlich auf den aufgeführten Quellen."
        )
        return "\n\n".join([intro] + body_sentences + [conclusion])

    def ask(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        results = self._search(question, top_k)
        answer = self._compose_answer(question, results)
        bibliography = self.bibliography.bibliography()
        return {
            "answer": answer,
            "results": results,
            "bibliography": bibliography,
            "citation_order": self.bibliography.citation_order(),
        }

    def chapter(self, title: str, topic: str, sections: int = 3) -> dict[str, Any]:
        query = f"{title} – {topic}"
        results = self._search(query, top_k=max(self.settings.top_k, sections))
        paragraphs = []
        for idx in range(min(sections, len(results))):
            chunk = results[idx]
            sentences = [s.strip() for s in chunk.text.split(".") if s.strip()]
            body = ". ".join(sentences[:3])
            citation = self.bibliography.cite(chunk.doc_id, page=chunk.page)
            paragraphs.append(f"{body}. {citation}")
        chapter_text = f"# {title}\n\n" + "\n\n".join(paragraphs)
        bibliography = self.bibliography.bibliography()
        return {
            "title": title,
            "topic": topic,
            "text": chapter_text,
            "bibliography": bibliography,
        }
