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
        mock_prop.property_type = 0  # Not INCR
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event, 999
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
        mock_prop.property_type = 0  # Not INCR
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event, 999
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
        mock_prop.property_type = 0  # Not INCR
        mock_window.get_full_property.return_value = mock_prop

        deferred_events: list[MagicMock] = []
        x11_event = asyncio.Event()

        assert not x11_event.is_set()

        await _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, x11_event, 999
        )

        assert x11_event.is_set()


class TestPropertyReadResult:
    """Tests for PropertyReadResult dataclass behavior."""

    def test_normal_content_result(self) -> None:
        """PropertyReadResult stores normal content correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=b"hello", is_incr=False)
        assert result.content == b"hello"
        assert result.is_incr is False
        assert result.estimated_size == 0

    def test_incr_result(self) -> None:
        """PropertyReadResult stores INCR detection correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=None, is_incr=True, estimated_size=1024)
        assert result.content is None
        assert result.is_incr is True
        assert result.estimated_size == 1024

    def test_failed_read_result(self) -> None:
        """PropertyReadResult represents failed read correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=None, is_incr=False)
        assert result.content is None
        assert result.is_incr is False
        assert result.estimated_size == 0

    def test_equality(self) -> None:
        """PropertyReadResult instances are equal when fields match."""
        from pclipsync.clipboard_io import PropertyReadResult

        r1 = PropertyReadResult(content=b"test", is_incr=False)
        r2 = PropertyReadResult(content=b"test", is_incr=False)
        assert r1 == r2

        r3 = PropertyReadResult(content=b"other", is_incr=False)
        assert r1 != r3


class TestReadSelectionProperty:
    """Tests for _read_selection_property function."""

    def test_normal_utf8_string_response(self) -> None:
        """Normal UTF8_STRING response returns content in PropertyReadResult."""
        from unittest.mock import MagicMock

        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456  # Different from property_type

        # Create mock property with UTF8_STRING type
        mock_prop = MagicMock()
        mock_prop.property_type = 789  # Not incr_atom
        mock_prop.value = b"test content"
        mock_window.get_full_property.return_value = mock_prop

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content == b"test content"
        assert result.is_incr is False
        assert result.estimated_size == 0

        # Verify property was deleted for non-INCR case
        mock_window.delete_property.assert_called_once_with(prop_atom)
        mock_display.flush.assert_called_once()

    def test_incr_response_detection(self) -> None:
        """INCR response returns is_incr=True with estimated_size."""
        from unittest.mock import MagicMock

        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456

        # Create mock property with INCR type and size value
        mock_prop = MagicMock()
        mock_prop.property_type = incr_atom  # Matches incr_atom
        # INCR value is a 4-byte little-endian integer representing estimated size
        estimated_size = 1048576  # 1 MB
        mock_prop.value = estimated_size.to_bytes(4, byteorder="little")
        mock_window.get_full_property.return_value = mock_prop

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content is None
        assert result.is_incr is True
        assert result.estimated_size == estimated_size

        # Verify property was NOT deleted for INCR case
        mock_window.delete_property.assert_not_called()

    def test_empty_property_returns_failure_result(self) -> None:
        """Empty/None property returns PropertyReadResult with content=None."""
        from unittest.mock import MagicMock

        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456

        mock_window.get_full_property.return_value = None

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content is None
        assert result.is_incr is False
        assert result.estimated_size == 0
