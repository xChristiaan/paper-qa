"""Project-level pytest configuration for optional plugins."""

from _pytest.config.argparsing import Parser


def pytest_addoption(parser: Parser) -> None:
    parser.addoption("--typeguard-packages", action="store", default="")
