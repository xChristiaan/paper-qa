"""Index construction for the BA-Agent."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

import numpy as np

try:  # pragma: no cover - runtime dependency optional
    import faiss  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - used when faiss is unavailable
    faiss = None

try:  # pragma: no cover - optional dependency
    from sentence_transformers import (  # type: ignore[import-not-found]  # noqa: I001
        SentenceTransformer,
    )
except Exception:  # pragma: no cover - executed when transformers unavailable
    SentenceTransformer = None

from .config import Settings


@dataclass(slots=True)
class Chunk:
    """A chunk of text used for retrieval."""

    doc_id: str
    page: int
    text: str
    chunk_id: int


class EmbeddingBackend:
    """Wrapper around sentence-transformers with a deterministic fallback."""

    def __init__(self, model_name: str, random_seed: int = 42) -> None:
        self.dimension = 384
        self.random_seed = random_seed
        self._load_model(model_name)

    def _load_model(self, model_name: str) -> None:
        if SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(model_name, device="cpu")
                self.dimension = int(self.model.get_sentence_embedding_dimension())
                self.encoder = self._encode_sentence_transformer
                return
            except Exception:  # pragma: no cover - executed when model unavailable
                self.model = None
        self.encoder = self._encode_fallback

    def _encode_sentence_transformer(self, texts: Sequence[str]) -> np.ndarray:
        embeddings = np.asarray(
            self.model.encode(list(texts), normalize_embeddings=True),
            dtype="float32",
        )
        return embeddings

    def _encode_fallback(self, texts: Sequence[str]) -> np.ndarray:
        rng = np.random.default_rng(self.random_seed)
        embeddings = np.zeros((len(texts), self.dimension), dtype="float32")
        for idx, text in enumerate(texts):
            encoded = text.encode("utf-8", errors="ignore")
            for byte_index, byte in enumerate(encoded):
                embeddings[idx, (byte_index + byte) % self.dimension] += 1.0
            if embeddings[idx].sum() == 0:
                embeddings[idx, :] = rng.random(self.dimension)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (embeddings / norms).astype("float32")

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        return self.encoder(texts)


class IndexBuilder:
    """Build the FAISS index and chunk metadata."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.backend = EmbeddingBackend(
            self.settings.embedding_model, self.settings.random_seed
        )

    def load_records(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        if not self.settings.pages_file.exists():
            msg = (
                "Es wurden keine eingelesenen Seiten gefunden. Bitte zuerst "
                "'ba-agent ingest' ausführen."
            )
            raise FileNotFoundError(msg)
        with self.settings.pages_file.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                data = json.loads(line)
                chunks.append(
                    Chunk(
                        doc_id=data["doc_id"],
                        page=int(data["page"]),
                        text=data["text"],
                        chunk_id=idx,
                    )
                )
        return chunks

    def chunk_text(self, records: Iterable[Chunk]) -> list[Chunk]:
        # Records are already page-level; we re-chunk to ensure size constraints
        chunks: list[Chunk] = []
        chunk_size_min = self.settings.chunk_min_size
        chunk_size_max = self.settings.chunk_max_size
        overlap = self.settings.chunk_overlap
        chunk_id = 0
        for record in records:
            text = record.text
            start = 0
            while start < len(text):
                end = min(start + chunk_size_max, len(text))
                candidate = text[start:end]
                if len(candidate) < chunk_size_min and end != len(text):
                    end = min(len(text), start + chunk_size_min)
                    candidate = text[start:end]
                chunks.append(
                    Chunk(
                        doc_id=record.doc_id,
                        page=record.page,
                        text=candidate,
                        chunk_id=chunk_id,
                    )
                )
                chunk_id += 1
                if end == len(text):
                    break
                start = max(0, end - overlap)
        return chunks

    def build(self) -> list[Chunk]:
        raw_records = self.load_records()
        chunks = self.chunk_text(raw_records)
        embeddings = self.backend.encode([chunk.text for chunk in chunks])
        self._store_embeddings(embeddings)
        self._store_chunks(chunks)
        return chunks

    def _store_chunks(self, chunks: list[Chunk]) -> None:
        payload = [asdict(chunk) for chunk in chunks]
        if not payload:
            self.settings.chunk_file.write_text("", encoding="utf-8")
            return
        self.settings.chunk_file.write_text(
            "\n".join(json.dumps(item, ensure_ascii=False) for item in payload) + "\n",
            encoding="utf-8",
        )

    def _store_embeddings(self, embeddings: np.ndarray) -> None:
        if faiss is not None:
            index = faiss.IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            faiss.write_index(index, str(self.settings.index_file))
        else:  # pragma: no cover - executed in environments without faiss
            np.savez(self.settings.embedding_file, embeddings=embeddings)


def load_embeddings(settings: Settings) -> tuple[Any, list[dict[str, object]]]:
    """Load embeddings and chunk metadata from disk."""

    if not settings.chunk_file.exists():
        msg = "Es wurde noch kein Index erstellt. Bitte 'ba-agent index' ausführen."
        raise FileNotFoundError(msg)
    with settings.chunk_file.open("r", encoding="utf-8") as fh:
        chunk_payload = [json.loads(line) for line in fh if line.strip()]
    if faiss is not None and settings.index_file.exists():
        index = faiss.read_index(str(settings.index_file))
        return index, chunk_payload
    data = np.load(settings.embedding_file)
    return data["embeddings"], chunk_payload
