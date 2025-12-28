"""Tests for clipboard modules.

Tests for clipboard.py, clipboard_io.py, clipboard_events.py, and
clipboard_selection.py using mocked python-xlib to avoid requiring X11.
"""

from unittest.mock import MagicMock, patch

import pytest


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

    def test_registers_for_both_selections(self) -> None:
        """Register for CLIPBOARD and PRIMARY selection events."""
        from pclipsync.clipboard_events import register_xfixes_events
        mock_display = MagicMock()
        mock_window = MagicMock()

        with patch("pclipsync.clipboard_events.xfixes") as mock_xfixes:
            register_xfixes_events(mock_display, mock_window)
            # Should call select_selection_input twice (CLIPBOARD and PRIMARY)
            assert mock_xfixes.select_selection_input.call_count == 2


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

    def test_collects_selection_request_events(self) -> None:
        """Collect SelectionRequest events."""
        from pclipsync.clipboard_selection import process_pending_events
        mock_display = MagicMock()
        mock_event = MagicMock()
        mock_event.type = 30  # X.SelectionRequest
        mock_display.pending_events.side_effect = [1, 0]
        mock_display.next_event.return_value = mock_event

        with patch("pclipsync.clipboard_selection.X") as mock_X:
            mock_X.SelectionRequest = 30
            result = process_pending_events(mock_display)
            assert len(result) == 1
