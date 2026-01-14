#!/usr/bin/env python3
"""Integration tests for INCR handling in _wait_for_selection."""
from unittest.mock import MagicMock, patch

import pytest


class TestWaitForSelectionIncrIntegration:
    """Integration tests for INCR handling in _wait_for_selection."""

    def test_incr_path_returns_accumulated_content(self) -> None:
        """INCR detection triggers _handle_incr_transfer and returns content."""
        from pclipsync.clipboard_io import _wait_for_selection, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        deferred: list = []

        mock_display.pending_events.side_effect = [1, 0]
        sel_notify = MagicMock()
        sel_notify.type = 31
        mock_display.next_event.return_value = sel_notify

        incr_result = PropertyReadResult(content=None, is_incr=True, estimated_size=1024)
        read_patch = patch("pclipsync.clipboard_io._read_selection_property", return_value=incr_result)
        incr_patch = patch("pclipsync.clipboard_io._handle_incr_transfer", return_value=b"INCR content")
        with read_patch as mock_read, incr_patch as mock_incr:
            result = _wait_for_selection(mock_display, mock_window, 123, deferred, 456, 5.0)

        assert result == b"INCR content"
        mock_read.assert_called_once()
        mock_incr.assert_called_once()

    def test_non_incr_path_returns_content_directly(self) -> None:
        """Non-INCR detection returns content from PropertyReadResult."""
        from pclipsync.clipboard_io import _wait_for_selection, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        deferred: list = []

        mock_display.pending_events.side_effect = [1, 0]
        sel_notify = MagicMock()
        sel_notify.type = 31
        mock_display.next_event.return_value = sel_notify

        normal_result = PropertyReadResult(content=b"normal content", is_incr=False)
        read_patch = patch("pclipsync.clipboard_io._read_selection_property", return_value=normal_result)
        incr_patch = patch("pclipsync.clipboard_io._handle_incr_transfer")
        with read_patch as mock_read, incr_patch as mock_incr:
            result = _wait_for_selection(mock_display, mock_window, 123, deferred, 456, 5.0)

        assert result == b"normal content"
        mock_read.assert_called_once()
        mock_incr.assert_not_called()
