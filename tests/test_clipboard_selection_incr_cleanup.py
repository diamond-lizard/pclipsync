#!/usr/bin/env python3
"""Tests for INCR transfer cleanup and unsubscribe behavior."""
from unittest.mock import MagicMock


def test_unsubscribe_incr_requestor_removes_transfer_and_unsubscribes() -> None:
    """Test cleanup removes transfer and unsubscribes when last for window."""
    from pclipsync.clipboard_selection import (
        unsubscribe_incr_requestor,
        IncrSendState,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    content = b"x" * 100

    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=100,
        start_time=0.0,
        completion_sent=True,  # Completion already sent
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    # Call cleanup
    unsubscribe_incr_requestor(mock_display, state, transfer_key, pending_incr_sends)

    # Verify transfer was removed from pending_incr_sends
    assert transfer_key not in pending_incr_sends
    assert len(pending_incr_sends) == 0

    # Verify unsubscribe was called (change_attributes with event_mask=0)
    mock_requestor.change_attributes.assert_called_once_with(event_mask=0)

    # Verify flush was called
    mock_display.flush.assert_called_once()

