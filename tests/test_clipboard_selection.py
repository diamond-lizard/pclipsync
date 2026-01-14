#!/usr/bin/env python3
"""Tests for clipboard selection request handling."""
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_display() -> MagicMock:
    """Create a mock X11 display."""
    display = MagicMock()
    # Return distinct atom values for each interned atom
    atom_map = {"TARGETS": 100, "UTF8_STRING": 101, "TIMESTAMP": 102}
    display.intern_atom.side_effect = lambda name: atom_map.get(name, 999)
    return display


@pytest.fixture
def mock_event() -> MagicMock:
    """Create a mock SelectionRequest event."""
    event = MagicMock()
    event.requestor = MagicMock()
    event.requestor.id = 12345
    event.property = 200
    event.selection = 300
    event.time = 987654321
    return event


def test_targets_includes_timestamp(mock_display: MagicMock, mock_event: MagicMock) -> None:
    """Test TARGETS response includes TIMESTAMP atom."""
    from Xlib import Xatom
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TARGETS (use mock_display.intern_atom return value)
    mock_event.target = 100  # TARGETS atom from fixture

    handle_selection_request(mock_display, mock_event, b"test content", None)

    # Verify change_property was called with targets list including TIMESTAMP
    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    targets_list = call_args[0][3]  # Fourth positional arg is the data
    # Check TIMESTAMP atom (102 from fixture) is in targets list
    assert 102 in targets_list


def test_timestamp_request_returns_integer(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request returns acquisition_time as 32-bit INTEGER."""
    from Xlib import Xatom
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TIMESTAMP
    mock_event.target = 102  # TIMESTAMP atom

    handle_selection_request(mock_display, mock_event, b"test content", 555666777)

    # Verify change_property was called with INTEGER type and acquisition_time
    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    prop_type = call_args[0][1]  # Second positional arg is property type
    format_bits = call_args[0][2]  # Third positional arg is format (32-bit)
    data = call_args[0][3]  # Fourth positional arg is the data
    assert prop_type == Xatom.INTEGER
    assert format_bits == 32
    assert data == [555666777]


def test_timestamp_request_has_valid_property(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request results in SelectionNotify with valid property."""
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 102  # TIMESTAMP atom
    original_property = mock_event.property

    handle_selection_request(mock_display, mock_event, b"test content", 555666777)

    # Property should NOT be set to X.NONE (which would indicate refusal)
    # The original property value should be preserved
    assert mock_event.property == original_property

    # Verify SelectionNotify was sent
    mock_event.requestor.send_event.assert_called_once()


def test_utf8_string_still_works(mock_display: MagicMock, mock_event: MagicMock) -> None:
    """Regression test: UTF8_STRING requests still work correctly."""
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 101  # UTF8_STRING atom
    content = b"test clipboard content"

    handle_selection_request(mock_display, mock_event, content, None)

    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    prop_type = call_args[0][1]
    format_bits = call_args[0][2]
    data = call_args[0][3]
    assert prop_type == 101  # UTF8_STRING
    assert format_bits == 8
    assert data == content


def test_unsupported_target_refused(mock_display: MagicMock, mock_event: MagicMock) -> None:
    """Regression test: unsupported targets are still refused."""
    from Xlib import X
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 999  # Unknown target

    handle_selection_request(mock_display, mock_event, b"test", None)

    # Property should be set to X.NONE
    assert mock_event.property == X.NONE


def test_timestamp_refused_when_acquisition_time_none(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request refused when acquisition_time is None."""
    from Xlib import X
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TIMESTAMP
    mock_event.target = 102  # TIMESTAMP atom

    handle_selection_request(mock_display, mock_event, b"test", None)

    # Property should be set to X.NONE (refused)
    assert mock_event.property == X.NONE
    # change_property should NOT be called
    mock_event.requestor.change_property.assert_not_called()

def test_process_pending_events_drains_deferred_first() -> None:
    """Deferred events are drained and prepended before pending events."""
    from unittest.mock import MagicMock

    from pclipsync.clipboard_selection import process_pending_events

    mock_display = MagicMock()
    mock_display.pending_events.return_value = 0  # No new pending events

    # Create mock deferred events
    deferred1 = MagicMock()
    deferred2 = MagicMock()
    deferred_events = [deferred1, deferred2]

    result = process_pending_events(mock_display, deferred_events)

    assert result == [deferred1, deferred2]


def test_process_pending_events_clears_deferred_list() -> None:
    """Deferred events list is cleared after draining."""
    from unittest.mock import MagicMock

    from pclipsync.clipboard_selection import process_pending_events

    mock_display = MagicMock()
    mock_display.pending_events.return_value = 0

    deferred_events = [MagicMock(), MagicMock()]

    process_pending_events(mock_display, deferred_events)

    assert deferred_events == []


def test_needs_incr_transfer_false_for_small_content() -> None:
    """Test needs_incr_transfer returns False for content under threshold."""
    from unittest.mock import MagicMock
    from pclipsync.clipboard_selection import needs_incr_transfer

    mock_display = MagicMock()
    # Set max_request_length to 65536 (256KB max property size)
    mock_display.info.max_request_length = 65536

    # Small content should not need INCR
    small_content = b"Hello, World!"
    assert needs_incr_transfer(small_content, mock_display) is False


def test_needs_incr_transfer_true_for_large_content() -> None:
    """Test needs_incr_transfer returns True for content exceeding threshold."""
    from unittest.mock import MagicMock
    from pclipsync.clipboard_selection import needs_incr_transfer, INCR_SAFETY_MARGIN

    mock_display = MagicMock()
    # Set max_request_length to 1000 (4000 bytes max, ~3600 with safety margin)
    mock_display.info.max_request_length = 1000

    # Calculate threshold (1000 * 4 * 0.9 = 3600)
    threshold = int(1000 * 4 * INCR_SAFETY_MARGIN)

    # Content exceeding threshold should need INCR
    large_content = b"x" * (threshold + 1)
    assert needs_incr_transfer(large_content, mock_display) is True
