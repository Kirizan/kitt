"""Tests for the comparison TUI module."""

from kitt.cli.compare_tui import check_textual_available


def test_textual_available():
    """Textual should be available since it's a dev dependency."""
    assert check_textual_available() is True
