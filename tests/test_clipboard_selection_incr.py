#!/usr/bin/env python3
"""Tests for INCR transfer detection."""
from unittest.mock import MagicMock


def test_needs_incr_transfer_false_for_small_content() -> None:
    """Test needs_incr_transfer returns False for content under threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer

    mock_display = MagicMock()
    # Set max_request_length to 65536 (256KB max property size)
    mock_display.info.max_request_length = 65536

    # Small content should not need INCR
    small_content = b"Hello, World!"
    assert needs_incr_transfer(small_content, mock_display) is False


def test_needs_incr_transfer_true_for_large_content() -> None:
    """Test needs_incr_transfer returns True for content exceeding threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer, INCR_SAFETY_MARGIN

    mock_display = MagicMock()
    # Set max_request_length to 1000 (4000 bytes max, ~3600 with safety margin)
    mock_display.info.max_request_length = 1000

    # Calculate threshold (1000 * 4 * 0.9 = 3600)
    threshold = int(1000 * 4 * INCR_SAFETY_MARGIN)

    # Content exceeding threshold should need INCR
    large_content = b"x" * (threshold + 1)
    assert needs_incr_transfer(large_content, mock_display) is True


def test_handle_selection_request_small_content_uses_direct_change_property() -> None:
    """Test that small content uses direct change_property, not INCR."""
    from pclipsync.clipboard_selection import handle_selection_request, IncrSendState

    mock_display = MagicMock()
    # Set max_request_length high enough that content is "small"
    mock_display.info.max_request_length = 65536  # 256KB max

    mock_event = MagicMock()
    mock_event.target = mock_display.intern_atom.return_value  # UTF8_STRING
    mock_event.requestor = MagicMock()
    mock_event.property = 123
    mock_event.selection = 456
    mock_event.time = 789

    # Make intern_atom return different values for different atoms
    def intern_atom_side_effect(name: str) -> int:
        atoms = {"TARGETS": 1, "UTF8_STRING": 2, "TIMESTAMP": 3}
        return atoms.get(name, 99)

    mock_display.intern_atom.side_effect = intern_atom_side_effect
    mock_event.target = 2  # UTF8_STRING

    small_content = b"Hello, World!"
    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 100

    handle_selection_request(
        mock_display,
        mock_event,
        small_content,
        acquisition_time=1000,
        pending_incr_sends=pending_incr_sends,
        incr_atom=incr_atom,
    )

    # Verify change_property was called with the content directly
    mock_event.requestor.change_property.assert_called_once_with(
        mock_event.property, 2, 8, small_content
    )
    # Verify no INCR transfer was initiated
    assert len(pending_incr_sends) == 0


def test_handle_selection_request_large_content_initiates_incr() -> None:
    """Test that large content initiates INCR transfer and creates pending entry."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.info.max_request_length = 100  # 400 bytes max, ~360 with margin

    mock_event = MagicMock()
    mock_event.requestor = MagicMock()
    mock_event.requestor.id = 12345
    mock_event.property = 123
    mock_event.selection = 456
    mock_event.time = 789

    # Make intern_atom return different values for different atoms
    def intern_atom_side_effect(name: str) -> int:
        atoms = {"TARGETS": 1, "UTF8_STRING": 2, "TIMESTAMP": 3}
        return atoms.get(name, 99)

    mock_display.intern_atom.side_effect = intern_atom_side_effect
    mock_event.target = 2  # UTF8_STRING

    # Large content exceeding threshold
    threshold = int(100 * 4 * INCR_SAFETY_MARGIN)
    large_content = b"x" * (threshold + 100)

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 100

    handle_selection_request(
        mock_display,
        mock_event,
        large_content,
        acquisition_time=1000,
        pending_incr_sends=pending_incr_sends,
        incr_atom=incr_atom,
    )

    # Verify INCR transfer was initiated - pending entry created
    transfer_key = (mock_event.requestor.id, mock_event.property)
    assert transfer_key in pending_incr_sends

    # Verify the IncrSendState was set up correctly
    state = pending_incr_sends[transfer_key]
    assert state.requestor == mock_event.requestor
    assert state.property_atom == mock_event.property
    assert state.target_atom == 2  # UTF8_STRING
    assert state.selection_atom == mock_event.selection
    assert state.content == large_content
    assert state.offset == 0
    assert state.completion_sent is False


def test_incr_response_has_correct_type_and_size() -> None:
    """Test INCR response writes INCR type with content length as value."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.info.max_request_length = 100

    mock_event = MagicMock()
    mock_event.requestor = MagicMock()
    mock_event.requestor.id = 12345
    mock_event.property = 123
    mock_event.selection = 456
    mock_event.time = 789

    def intern_atom_side_effect(name: str) -> int:
        atoms = {"TARGETS": 1, "UTF8_STRING": 2, "TIMESTAMP": 3}
        return atoms.get(name, 99)

    mock_display.intern_atom.side_effect = intern_atom_side_effect
    mock_event.target = 2  # UTF8_STRING

    # Large content exceeding threshold
    threshold = int(100 * 4 * INCR_SAFETY_MARGIN)
    large_content = b"x" * (threshold + 100)
    content_length = len(large_content)

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 999  # The INCR atom value

    handle_selection_request(
        mock_display,
        mock_event,
        large_content,
        acquisition_time=1000,
        pending_incr_sends=pending_incr_sends,
        incr_atom=incr_atom,
    )

    # Verify change_property was called with INCR type and content length
    mock_event.requestor.change_property.assert_called_once_with(
        mock_event.property,  # property
        incr_atom,  # type = INCR
        32,  # format (32-bit integer)
        [content_length],  # data = content length
    )

    # Verify SelectionNotify was sent to requestor
    mock_event.requestor.send_event.assert_called_once()
    call_args = mock_event.requestor.send_event.call_args
    notify_event = call_args[0][0]
    assert notify_event.property == mock_event.property
    assert notify_event.target == mock_event.target
    assert notify_event.selection == mock_event.selection
