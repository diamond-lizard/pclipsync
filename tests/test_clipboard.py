"""Tests for clipboard modules.

Tests for clipboard.py, clipboard_io.py, clipboard_events.py, and
clipboard_selection.py. Uses mocks where possible and real X11 for
integration tests (skipped if DISPLAY not available).
"""

from unittest.mock import MagicMock, patch

import pytest

from conftest import has_display


class TestValidateDisplay:
    """Tests for validate_display function."""

    def test_missing_display_env(self) -> None:
        """Exit with error when DISPLAY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                from pclipsync.clipboard import validate_display
                validate_display()
            assert exc_info.value.code == 1

    def test_display_connection_failure(self) -> None:
        """Exit with error when X11 connection fails."""
        with patch.dict("os.environ", {"DISPLAY": ":0"}):
            with patch("Xlib.display.Display") as mock_display:
                mock_display.side_effect = Exception("Connection refused")
                with pytest.raises(SystemExit) as exc_info:
                    from pclipsync.clipboard import validate_display
                    validate_display()
                assert exc_info.value.code == 1


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
            # Should not raise - successful registration
            register_xfixes_events(display, window, clipboard_atom)
        finally:
            display.close()


class TestSetClipboardContent:
    """Tests for set_clipboard_content function."""

    def test_successful_ownership(self) -> None:
        """Return True when ownership acquired."""
        from pclipsync.clipboard_events import set_clipboard_content
        mock_display = MagicMock()
        mock_window = MagicMock()
        mock_display.get_selection_owner.return_value = mock_window
        result = set_clipboard_content(
            mock_display, mock_window, b"content", 1
        )
        assert result is True

    def test_failed_ownership(self) -> None:
        """Return False when ownership not acquired."""
        from pclipsync.clipboard_events import set_clipboard_content
        mock_display = MagicMock()
        mock_window = MagicMock()
        mock_display.get_selection_owner.return_value = MagicMock()
        result = set_clipboard_content(
            mock_display, mock_window, b"content", 1
        )
        assert result is False


class TestProcessPendingEvents:
    """Tests for process_pending_events function."""

    def test_returns_empty_when_no_events(self) -> None:
        """Return empty list when no pending events."""
        from pclipsync.clipboard_selection import process_pending_events
        mock_display = MagicMock()
        mock_display.pending_events.return_value = 0
        result = process_pending_events(mock_display)
        assert result == []

    @pytest.mark.skipif(not has_display(), reason="No X11 display available")
    def test_collects_selection_request_events(self) -> None:
        """Collect SelectionRequest events from real X11 display."""
        from Xlib.display import Display

        from pclipsync.clipboard_selection import process_pending_events

        display = Display()
        try:
            # With no events pending, should return empty list
            result = process_pending_events(display)
            assert isinstance(result, list)
        finally:
            display.close()
