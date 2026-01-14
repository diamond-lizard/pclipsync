"""Tests for clipboard content and event processing functions.

Tests for set_clipboard_content and process_pending_events.
"""

from unittest.mock import MagicMock

import pytest

from conftest import has_display


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
            result = process_pending_events(display)
            assert isinstance(result, list)
        finally:
            display.close()
