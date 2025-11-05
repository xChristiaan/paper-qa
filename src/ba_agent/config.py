"""Configuration for the BA-Agent project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class CitationLabel(BaseModel):
    """Representation of a single citation occurrence."""

    reference_id: str
    page: int | None = None

    def label(self) -> str:
        """Return the IEEE-style label for the citation."""

        if self.page is None:
            return f"[{self.reference_id}]"
        return f"[{self.reference_id}, p. {self.page}]"


class Settings(BaseSettings):
    """Project wide settings with sane defaults."""

    project_name: str = Field(default="ba-agent", alias="PROJECT_NAME")
    citation_style: str = Field(default="IEEE", alias="CITATION_STYLE")
    source_dir: Path = Field(default=Path("./quellen"), alias="SOURCE_DIR")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    pages_file: Path = Field(default=Path("./data/pages.jsonl"), alias="PAGES_FILE")
    chunk_file: Path = Field(default=Path("./data/chunks.jsonl"), alias="CHUNK_FILE")
    index_file: Path = Field(default=Path("./data/index.faiss"), alias="INDEX_FILE")
    embedding_file: Path = Field(
        default=Path("./data/embeddings.npz"), alias="EMBEDDING_FILE"
    )
    metadata_file: Path = Field(
        default=Path("./data/sources.json"), alias="METADATA_FILE"
    )
    bib_file: Path = Field(
        default=Path("./metadata/zotero.csl.json"), alias="BIB_FILE"
    )
    csl_file: Path = Field(default=Path("./metadata/ieee.csl"), alias="CSL_FILE")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    chunk_min_size: int = Field(default=800, alias="CHUNK_MIN_SIZE")
    chunk_max_size: int = Field(default=1200, alias="CHUNK_MAX_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")
    top_k: int = Field(default=5, alias="TOP_K")
    random_seed: int = Field(default=42, alias="RANDOM_SEED")

    class Config:
        env_file = ".env"
        populate_by_name = True

    def ensure_directories(self) -> None:
        """Ensure that data directories exist."""

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.source_dir.mkdir(parents=True, exist_ok=True)
        self.bib_file.parent.mkdir(parents=True, exist_ok=True)

    def model_post_init(self, __context: Any) -> None:  # pragma: no cover
        self.ensure_directories()
