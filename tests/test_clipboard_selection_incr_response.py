#!/usr/bin/env python3
"""Tests for INCR response format (type and size)."""
from unittest.mock import MagicMock


def test_incr_response_has_correct_type_and_size() -> None:
    """Test INCR response writes INCR type with content length as value."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.display.info.max_request_length = 100

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
