#!/usr/bin/env python3
"""Tests for clipboard_io module.

Tests for _wait_for_selection and read_clipboard_content functions,
focusing on deferred event collection during polling.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from Xlib import X


class TestWaitForSelectionDeferredEvents:
    """Tests for event deferral during _wait_for_selection polling."""

    @pytest.mark.asyncio
    async def test_defers_selection_request_events(self) -> None:
        """SelectionRequest events are added to deferred_events during polling."""
        from pclipsync.clipboard_io import _wait_for_selection

        # Create mock display that returns a SelectionRequest then SelectionNotify
        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        # Create mock events
        sel_request = MagicMock()
        sel_request.type = X.SelectionRequest

        sel_notify = MagicMock()
        sel_notify.type = X.SelectionNotify

        # Set up pending_events to return 1, 1, 0 (two events then done)
        mock_display.pending_events.side_effect = [1, 1, 0]
        mock_display.next_event.side_effect = [sel_request, sel_notify]

        # Mock property read
        mock_prop = MagicMock()
        mock_prop.value = b"test content"
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event
        )

        assert len(deferred_events) == 1
        assert deferred_events[0] is sel_request

    @pytest.mark.asyncio
    async def test_defers_owner_notify_events(self) -> None:
        """SetSelectionOwnerNotify events are added to deferred_events."""
        from pclipsync.clipboard_io import _wait_for_selection

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123

        # Create mock SetSelectionOwnerNotify (XFixes event)
        owner_event = MagicMock()
        owner_event.type = 999  # Not a standard X event type
        owner_event.__class__.__name__ = "SetSelectionOwnerNotify"

        sel_notify = MagicMock()
        sel_notify.type = X.SelectionNotify

        mock_display.pending_events.side_effect = [1, 1, 0]
        mock_display.next_event.side_effect = [owner_event, sel_notify]

        mock_prop = MagicMock()
        mock_prop.value = b"test"
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event
        )

        assert len(deferred_events) == 1
        assert deferred_events[0] is owner_event

    @pytest.mark.asyncio
    async def test_signals_x11_event_when_events_deferred(self) -> None:
        """x11_event.set() is called when events are deferred."""
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
        mock_prop.value = b"test"
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        assert not x11_event.is_set()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event
        )

        assert x11_event.is_set()
