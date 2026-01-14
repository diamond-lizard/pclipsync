#!/usr/bin/env python3
"""Tests for send_incr_chunk first chunk behavior."""
from unittest.mock import MagicMock


def test_send_incr_chunk_first_chunk() -> None:
    """Test send_incr_chunk sends correct first chunk from offset 0."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    # Create content larger than one chunk
    content = b"x" * (INCR_CHUNK_SIZE + 100)

    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=0,
        start_time=0.0,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    send_incr_chunk(mock_display, state, transfer_key, pending_incr_sends)

    # Verify first chunk was written
    expected_chunk = content[:INCR_CHUNK_SIZE]
    mock_requestor.change_property.assert_called_once_with(
        123,  # property_atom
        456,  # target_atom
        8,    # format
        expected_chunk,
    )

    # Verify offset was updated
    assert state.offset == INCR_CHUNK_SIZE

    # Verify completion_sent is still False
    assert state.completion_sent is False

    # Verify flush was called
    mock_display.flush.assert_called_once()
