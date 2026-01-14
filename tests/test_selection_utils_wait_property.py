#!/usr/bin/env python3
"""Tests for wait_for_property_notify function.

Uses mocks for X11 display to avoid requiring a real display.
"""

from unittest.mock import MagicMock

from Xlib import X

from pclipsync.selection_utils import wait_for_property_notify


class TestWaitForPropertyNotify:
    """Tests for wait_for_property_notify function."""

    def test_returns_matching_property_notify_immediately(self) -> None:
        """Return immediately when PropertyNotify matches all criteria."""
        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        mock_event = MagicMock()
        mock_event.type = X.PropertyNotify
        mock_event.window = mock_window
        mock_event.atom = prop_atom
        mock_event.state = X.PropertyNewValue

        mock_display.next_event.return_value = mock_event
        mock_display.pending_events.return_value = 1

        deferred: list = []
        result = wait_for_property_notify(
            mock_display, mock_window, prop_atom, deferred, timeout=1.0
        )

        assert result == mock_event
        assert deferred == []

    def test_defers_selection_request_before_match(self) -> None:
        """Defer SelectionRequest events until matching PropertyNotify found."""
        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        req_event = MagicMock()
        req_event.type = X.SelectionRequest

        target_event = MagicMock()
        target_event.type = X.PropertyNotify
        target_event.window = mock_window
        target_event.atom = prop_atom
        target_event.state = X.PropertyNewValue

        mock_display.next_event.side_effect = [req_event, target_event]
        mock_display.pending_events.side_effect = [1, 1, 0]

        deferred: list = []
        result = wait_for_property_notify(
            mock_display, mock_window, prop_atom, deferred, timeout=1.0
        )

        assert result == target_event
        assert deferred == [req_event]

    def test_defers_set_selection_owner_notify_before_match(self) -> None:
        """Defer SetSelectionOwnerNotify events until matching PropertyNotify found."""
        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        owner_event = MagicMock()
        owner_event.type = 999  # Non-standard type
        type(owner_event).__name__ = "SetSelectionOwnerNotify"

        target_event = MagicMock()
        target_event.type = X.PropertyNotify
        target_event.window = mock_window
        target_event.atom = prop_atom
        target_event.state = X.PropertyNewValue

        mock_display.next_event.side_effect = [owner_event, target_event]
        mock_display.pending_events.side_effect = [1, 1, 0]

        deferred: list = []
        result = wait_for_property_notify(
            mock_display, mock_window, prop_atom, deferred, timeout=1.0
        )

        assert result == target_event
        assert deferred == [owner_event]
