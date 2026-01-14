#!/usr/bin/env python3
"""Tests for send_incr_chunk subsequent chunk behavior."""
from unittest.mock import MagicMock


def test_send_incr_chunk_subsequent_chunk() -> None:
    """Test send_incr_chunk sends correct subsequent chunk with offset."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    # Create content larger than two chunks
    content = b"x" * (INCR_CHUNK_SIZE * 2 + 100)

    # Start from offset = INCR_CHUNK_SIZE (simulating second chunk)
    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=INCR_CHUNK_SIZE,  # Start at second chunk
        start_time=0.0,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    send_incr_chunk(mock_display, state, transfer_key, pending_incr_sends)

    # Verify second chunk was written
    expected_chunk = content[INCR_CHUNK_SIZE:INCR_CHUNK_SIZE * 2]
    mock_requestor.change_property.assert_called_once_with(
        123,  # property_atom
        456,  # target_atom
        8,    # format
        expected_chunk,
    )

    # Verify offset was updated to 2 * INCR_CHUNK_SIZE
    assert state.offset == INCR_CHUNK_SIZE * 2

    # Verify completion_sent is still False
    assert state.completion_sent is False
