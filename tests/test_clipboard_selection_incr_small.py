#!/usr/bin/env python3
"""Tests for small content direct clipboard transfer (non-INCR)."""
from unittest.mock import MagicMock


def test_handle_selection_request_small_content_uses_direct_change_property() -> None:
    """Test that small content uses direct change_property, not INCR."""
    from pclipsync.clipboard_selection import handle_selection_request, IncrSendState

    mock_display = MagicMock()
    # Set max_request_length high enough that content is "small"
    mock_display.display.info.max_request_length = 65536  # 256KB max

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
