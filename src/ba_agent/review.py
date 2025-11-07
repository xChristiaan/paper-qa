"""Reviewer agent ensuring IEEE citation compliance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

CITATION_PATTERN = re.compile(r"\[(\d+)(?:, p\. (\d+))?\]")


@dataclass(slots=True)
class ReviewWarning:
    code: str
    message: str
    context: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "context": self.context}


class Reviewer:
    """Validate texts according to IEEE rules."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.warnings: list[ReviewWarning] = []

    def _check_citation_presence(self) -> None:
        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", self.text)
            if sentence.strip()
        ]
        for sentence in sentences:
            if sentence.lower().startswith("abb."):
                continue
            if not CITATION_PATTERN.search(sentence):
                self.warnings.append(
                    ReviewWarning(
                        code="missing-citation",
                        message="Satz ohne IEEE-Zitation gefunden.",
                        context=sentence,
                    )
                )

    def _check_sequence(self) -> None:
        numbers = [
            int(match.group(1))
            for match in CITATION_PATTERN.finditer(self.text)
        ]
        if not numbers:
            return
        expected = list(range(1, numbers[-1] + 1))
        if numbers != expected:
            self.warnings.append(
                ReviewWarning(
                    code="sequence-error",
                    message="Zitationsnummern sind nicht fortlaufend ohne Lücken.",
                    context=str(numbers),
                )
            )
        if len(set(numbers)) != len(numbers):
            self.warnings.append(
                ReviewWarning(
                    code="duplicate-reference",
                    message="Zitationsnummer wird mehrfach verwendet.",
                    context=str(numbers),
                )
            )

    def _check_format(self) -> None:
        for match in CITATION_PATTERN.finditer(self.text):
            if match.group(2) and not match.group(0).endswith(match.group(2) + "]"):
                self.warnings.append(
                    ReviewWarning(
                        code="format-error",
                        message="Seitenzahlen müssen als 'p.' angegeben werden.",
                        context=match.group(0),
                    )
                )

    def review(self) -> dict[str, list[dict[str, str | None]]]:
        self._check_citation_presence()
        self._check_sequence()
        self._check_format()
        return {"warnings": [warning.to_dict() for warning in self.warnings]}


def review_file(path: Path) -> dict[str, list[dict[str, str | None]]]:
    text = path.read_text(encoding="utf-8")
    reviewer = Reviewer(text)
    return reviewer.review()
