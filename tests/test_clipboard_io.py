#!/usr/bin/env python3
"""Tests for clipboard_io module.

Tests for _wait_for_selection and read_clipboard_content functions,
focusing on deferred event collection during polling.
"""
from unittest.mock import MagicMock

import pytest

from Xlib import X


class TestWaitForSelectionDeferredEvents:
    """Tests for event deferral during _wait_for_selection polling."""

    def test_defers_selection_request_events(self) -> None:
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

        _wait_for_selection(
            mock_display, mock_window, prop_atom, deferred_events, 999, 5.0
        )

        assert len(deferred_events) == 1
        assert deferred_events[0] is owner_event

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


class TestHandleIncrTransfer:
    """Tests for _handle_incr_transfer function."""

    def test_successful_three_chunk_transfer(self) -> None:
        """Successful 3-chunk INCR transfer assembles buffer correctly."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        deferred_events: list = []
        chunk_timeout = 5.0

        # Mock PropertyNotify events for 3 chunks + end marker
        mock_event = MagicMock()

        # Chunks: "Hello", " ", "World" -> "Hello World"
        chunks = [b"Hello", b" ", b"World", b""]  # Empty = end marker

        with patch(
            "pclipsync.selection_utils.wait_for_property_notify",
            return_value=mock_event,
        ) as mock_wait, patch(
            "pclipsync.clipboard_io._read_chunk_property",
            side_effect=chunks,
        ) as mock_read:
            result = _handle_incr_transfer(
                mock_display, mock_window, prop_atom, deferred_events, chunk_timeout
            )

        assert result == b"Hello World"
        # Initial handshake: delete property and flush
        mock_window.delete_property.assert_called_with(prop_atom)
        mock_display.flush.assert_called()
        # wait_for_property_notify called 4 times (3 chunks + end marker)
        assert mock_wait.call_count == 4
        # _read_chunk_property called 4 times
        assert mock_read.call_count == 4

    def test_immediate_zero_length_chunk(self) -> None:
        """INCR transfer with immediate zero-length chunk returns empty bytes."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        deferred_events: list = []
        chunk_timeout = 5.0

        mock_event = MagicMock()

        # Immediate empty chunk = empty content
        chunks = [b""]

        with patch(
            "pclipsync.selection_utils.wait_for_property_notify",
            return_value=mock_event,
        ) as mock_wait, patch(
            "pclipsync.clipboard_io._read_chunk_property",
            side_effect=chunks,
        ):
            result = _handle_incr_transfer(
                mock_display, mock_window, prop_atom, deferred_events, chunk_timeout
            )

        assert result == b""
        assert mock_wait.call_count == 1

    def test_timeout_on_second_chunk(self) -> None:
        """INCR transfer times out on second chunk returns None."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        deferred_events: list = []
        chunk_timeout = 5.0

        mock_event = MagicMock()

        # First chunk succeeds, second times out (None from wait_for_property_notify)
        wait_returns = [mock_event, None]
        chunks = [b"Hello"]  # Only first chunk returned before timeout

        with patch(
            "pclipsync.selection_utils.wait_for_property_notify",
            side_effect=wait_returns,
        ) as mock_wait, patch(
            "pclipsync.clipboard_io._read_chunk_property",
            side_effect=chunks,
        ):
            result = _handle_incr_transfer(
                mock_display, mock_window, prop_atom, deferred_events, chunk_timeout
            )

        assert result is None
        # Called twice: once for first chunk, once for second (timed out)
        assert mock_wait.call_count == 2

    def test_exceeds_max_content_size(self) -> None:
        """INCR transfer exceeding MAX_CONTENT_SIZE returns None."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _handle_incr_transfer
        from pclipsync.protocol import MAX_CONTENT_SIZE

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        deferred_events: list = []
        chunk_timeout = 5.0

        mock_event = MagicMock()

        # Create chunks that exceed MAX_CONTENT_SIZE
        # Each chunk is half the max size, so two chunks exceed it
        chunk_size = (MAX_CONTENT_SIZE // 2) + 1
        large_chunk = b"x" * chunk_size
        chunks = [large_chunk, large_chunk]  # Total exceeds MAX_CONTENT_SIZE

        with patch(
            "pclipsync.selection_utils.wait_for_property_notify",
            return_value=mock_event,
        ), patch(
            "pclipsync.clipboard_io._read_chunk_property",
            side_effect=chunks,
        ):
            result = _handle_incr_transfer(
                mock_display, mock_window, prop_atom, deferred_events, chunk_timeout
            )

        assert result is None

    def test_deferred_events_accumulate_selection_requests(self) -> None:
        """INCR transfer defers SelectionRequest events to deferred_events list."""
        from unittest.mock import MagicMock, patch, call

        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        deferred_events: list = []
        chunk_timeout = 5.0

        mock_event = MagicMock()

        # Create a mock SelectionRequest that will be in deferred_events
        # after wait_for_property_notify processes it
        mock_selection_request = MagicMock()
        mock_selection_request.type = "SelectionRequest"

        # wait_for_property_notify adds to deferred_events internally
        # We simulate this by having the side_effect modify deferred_events
        def wait_side_effect(*args, **kwargs):
            # args[3] is deferred_events list
            args[3].append(mock_selection_request)
            return mock_event

        chunks = [b"data", b""]  # One chunk + end marker

        with patch(
            "pclipsync.selection_utils.wait_for_property_notify",
            side_effect=wait_side_effect,
        ), patch(
            "pclipsync.clipboard_io._read_chunk_property",
            side_effect=chunks,
        ):
            result = _handle_incr_transfer(
                mock_display, mock_window, prop_atom, deferred_events, chunk_timeout
            )

        assert result == b"data"
        # Deferred events should have accumulated SelectionRequest events
        # (one per wait_for_property_notify call = 2 calls for chunk + end marker)
        assert len(deferred_events) == 2
        assert all(e.type == "SelectionRequest" for e in deferred_events)


class TestWaitForSelectionIncrIntegration:
    """Integration tests for INCR handling in _wait_for_selection."""

    def test_incr_path_returns_accumulated_content(self) -> None:
        """INCR detection triggers _handle_incr_transfer and returns content."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _wait_for_selection, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456
        deferred_events: list = []

        # Mock SelectionNotify event
        mock_display.pending_events.side_effect = [1, 0]
        sel_notify = MagicMock()
        sel_notify.type = 31  # X.SelectionNotify
        mock_display.next_event.return_value = sel_notify

        # Mock property read to return INCR
        incr_result = PropertyReadResult(content=None, is_incr=True, estimated_size=1024)
        with patch(
            "pclipsync.clipboard_io._read_selection_property",
            return_value=incr_result,
        ) as mock_read, patch(
            "pclipsync.clipboard_io._handle_incr_transfer",
            return_value=b"INCR content",
        ) as mock_incr:
            result = _wait_for_selection(
                mock_display, mock_window, prop_atom, deferred_events, incr_atom, 5.0
            )

        assert result == b"INCR content"
        mock_read.assert_called_once()
        mock_incr.assert_called_once()

    def test_non_incr_path_returns_content_directly(self) -> None:
        """Non-INCR detection returns content from PropertyReadResult."""
        from unittest.mock import MagicMock, patch

        from pclipsync.clipboard_io import _wait_for_selection, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456
        deferred_events: list = []

        # Mock SelectionNotify event
        mock_display.pending_events.side_effect = [1, 0]
        sel_notify = MagicMock()
        sel_notify.type = 31  # X.SelectionNotify
        mock_display.next_event.return_value = sel_notify

        # Mock property read to return normal content (non-INCR)
        normal_result = PropertyReadResult(content=b"normal content", is_incr=False)
        with patch(
            "pclipsync.clipboard_io._read_selection_property",
            return_value=normal_result,
        ) as mock_read, patch(
            "pclipsync.clipboard_io._handle_incr_transfer",
        ) as mock_incr:
            result = _wait_for_selection(
                mock_display, mock_window, prop_atom, deferred_events, incr_atom, 5.0
            )

        assert result == b"normal content"
        mock_read.assert_called_once()
        mock_incr.assert_not_called()
