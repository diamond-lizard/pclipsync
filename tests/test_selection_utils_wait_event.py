#!/usr/bin/env python3
"""Tests for wait_for_event_type function.

Uses mocks for X11 display to avoid requiring a real display.
"""

from unittest.mock import MagicMock

from Xlib import X

from pclipsync.selection_utils import wait_for_event_type


class TestWaitForEventType:
    """Tests for wait_for_event_type function."""

    def test_returns_matching_event_immediately(self) -> None:
        """Return immediately when first event matches target type."""
        mock_display = MagicMock()
        mock_event = MagicMock()
        mock_event.type = X.SelectionNotify
        mock_display.next_event.return_value = mock_event
        mock_display.pending_events.return_value = 1

        deferred: list = []
        result = wait_for_event_type(
            mock_display, X.SelectionNotify, deferred, timeout=1.0
        )

        assert result == mock_event
        assert deferred == []

    def test_defers_selection_request_events(self) -> None:
        """Defer SelectionRequest events until target found."""
        mock_display = MagicMock()

        req_event = MagicMock()
        req_event.type = X.SelectionRequest

        target_event = MagicMock()
        target_event.type = X.PropertyNotify

        mock_display.next_event.side_effect = [req_event, target_event]
        mock_display.pending_events.side_effect = [1, 1, 0]

        deferred: list = []
        result = wait_for_event_type(
            mock_display, X.PropertyNotify, deferred, timeout=1.0
        )

        assert result == target_event
        assert deferred == [req_event]

    def test_defers_set_selection_owner_notify(self) -> None:
        """Defer SetSelectionOwnerNotify events until target found."""
        mock_display = MagicMock()

        owner_event = MagicMock()
        owner_event.type = 999  # Non-standard type
        type(owner_event).__name__ = "SetSelectionOwnerNotify"

        target_event = MagicMock()
        target_event.type = X.SelectionNotify

        mock_display.next_event.side_effect = [owner_event, target_event]
        mock_display.pending_events.side_effect = [1, 1, 0]

        deferred: list = []
        result = wait_for_event_type(
            mock_display, X.SelectionNotify, deferred, timeout=1.0
        )

        assert result == target_event
        assert deferred == [owner_event]
