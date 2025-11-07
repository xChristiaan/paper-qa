"""Tests for IEEE citation formatting."""

from __future__ import annotations

from ba_agent.review import CITATION_PATTERN


def test_ieee_regex_allows_page_numbers() -> None:
    pattern = CITATION_PATTERN
    assert pattern.fullmatch("[1]")
    assert pattern.fullmatch("[12, p. 45]")
    assert pattern.fullmatch("[3, p. 7]")


def test_ieee_regex_rejects_invalid_format() -> None:
    pattern = CITATION_PATTERN
    assert pattern.fullmatch("(1)") is None
    assert pattern.fullmatch("[1, pp. 45]") is None
    assert pattern.fullmatch("[1, Seite 45]") is None
