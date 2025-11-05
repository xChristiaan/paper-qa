"""Minimal CiteProcJSON source implementation."""

from __future__ import annotations

from typing import Iterable


class CiteProcJSON:
    """Store CSL JSON entries for lookup."""

    def __init__(self, items: Iterable[dict[str, object]]) -> None:
        self._items = {item["id"]: item for item in items if "id" in item}

    def get_reference(self, key: str) -> dict[str, object]:
        return dict(self._items.get(key, {"id": key}))

    def __iter__(self):  # pragma: no cover - legacy compatibility
        return iter(self._items.values())
