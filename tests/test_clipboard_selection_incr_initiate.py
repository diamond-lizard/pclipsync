#!/usr/bin/env python3
"""Tests for INCR transfer initiation with large content."""
from unittest.mock import MagicMock


def test_handle_selection_request_large_content_initiates_incr() -> None:
    """Test that large content initiates INCR transfer and creates pending entry."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.display.info.max_request_length = 100  # 400 bytes max, ~360 with margin

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
