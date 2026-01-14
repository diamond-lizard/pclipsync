"""Tests for clipboard display and window functions.

Tests for get_display_fd, create_hidden_window, and register_xfixes_events.
"""

from unittest.mock import MagicMock

import pytest

from conftest import has_display


class TestGetDisplayFd:
    """Tests for get_display_fd function."""

    def test_returns_file_descriptor(self) -> None:
        """Return file descriptor from display."""
        from pclipsync.clipboard import get_display_fd
        mock_display = MagicMock()
        mock_display.fileno.return_value = 42
        result = get_display_fd(mock_display)
        assert result == 42


class TestCreateHiddenWindow:
    """Tests for create_hidden_window function."""

    def test_creates_window(self) -> None:
        """Create a 1x1 window."""
        from pclipsync.clipboard import create_hidden_window
        mock_display = MagicMock()
        mock_window = MagicMock()
        mock_display.screen().root.create_window.return_value = mock_window
        result = create_hidden_window(mock_display)
        assert result == mock_window


class TestRegisterXfixesEvents:
    """Tests for register_xfixes_events function."""

    @pytest.mark.skipif(not has_display(), reason="No X11 display available")
    def test_registers_for_both_selections(self) -> None:
        """Register for CLIPBOARD and PRIMARY selection events."""
        from Xlib.display import Display

        from pclipsync.clipboard import create_hidden_window
        from pclipsync.clipboard_events import register_xfixes_events

        display = Display()
        try:
            window = create_hidden_window(display)
            clipboard_atom = display.intern_atom("CLIPBOARD")
            register_xfixes_events(display, window, clipboard_atom)
        finally:
            display.close()
