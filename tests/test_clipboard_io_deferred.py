#!/usr/bin/env python3
"""Tests for deferred event collection during _wait_for_selection polling."""
from unittest.mock import MagicMock

import pytest

from Xlib import X


class TestWaitForSelectionDeferredEvents:
    """Tests for event deferral during _wait_for_selection polling."""

    def test_defers_selection_request_events(self) -> None:
        """SelectionRequest events are added to deferred_events during polling."""
        from pclipsync.clipboard_io import _wait_for_selection

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        sel_request = MagicMock()
        sel_request.type = X.SelectionRequest

        sel_notify = MagicMock()
        sel_notify.type = X.SelectionNotify

        mock_display.pending_events.side_effect = [1, 1, 0]
        mock_display.next_event.side_effect = [sel_request, sel_notify]

        mock_prop = MagicMock()
        mock_prop.value = b"test content"
        mock_prop.property_type = 0
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []

        _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, 999, 5.0
        )

        assert len(deferred_events) == 1
        assert deferred_events[0] is sel_request

    def test_defers_owner_notify_events(self) -> None:
        """SetSelectionOwnerNotify events are added to deferred_events."""
        from pclipsync.clipboard_io import _wait_for_selection

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        owner_event = MagicMock()
        owner_event.type = 999
        owner_event.__class__.__name__ = "SetSelectionOwnerNotify"

        sel_notify = MagicMock()
        sel_notify.type = X.SelectionNotify

        mock_display.pending_events.side_effect = [1, 1, 0]
        mock_display.next_event.side_effect = [owner_event, sel_notify]

        mock_prop = MagicMock()
        mock_prop.value = b"test"
        mock_prop.property_type = 0
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []

        _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, 999, 5.0
        )

        assert len(deferred_events) == 1
        assert deferred_events[0] is owner_event
