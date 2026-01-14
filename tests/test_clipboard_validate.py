"""Tests for validate_display function.

Tests clipboard display validation with mocked X11 connections.
"""

from unittest.mock import patch

import pytest


def _validate_with_no_display() -> int:
    """Call validate_display with DISPLAY unset and return exit code."""
    with patch.dict("os.environ", {}, clear=True):
        try:
            from pclipsync.clipboard import validate_display
            validate_display()
            return 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1


def _validate_with_connection_failure() -> int:
    """Call validate_display with X11 connection failure and return exit code."""
    with patch.dict("os.environ", {"DISPLAY": ":0"}), \
        patch("Xlib.display.Display") as mock_display:
        mock_display.side_effect = Exception("Connection refused")
        try:
            from pclipsync.clipboard import validate_display
            validate_display()
            return 0
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1


class TestValidateDisplay:
    """Tests for validate_display function."""

    def test_missing_display_env(self) -> None:
        """Exit with error when DISPLAY is not set."""
        exit_code = _validate_with_no_display()
        assert exit_code == 1

    def test_display_connection_failure(self) -> None:
        """Exit with error when X11 connection fails."""
        exit_code = _validate_with_connection_failure()
        assert exit_code == 1
