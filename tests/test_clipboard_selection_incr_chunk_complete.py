#!/usr/bin/env python3
"""Tests for send_incr_chunk completion behavior."""
from unittest.mock import MagicMock


def test_send_incr_chunk_zero_length_completion() -> None:
    """Test send_incr_chunk sends zero-length chunk when all content sent."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    content = b"x" * 100

    # Set offset >= content length (all content already sent)
    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=100,  # All content sent
        start_time=0.0,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    send_incr_chunk(mock_display, state, transfer_key, pending_incr_sends)

    # Verify zero-length chunk was written
    mock_requestor.change_property.assert_called_once_with(
        123,  # property_atom
        456,  # target_atom
        8,    # format
        b"",  # zero-length data
    )

    # Verify flush was called
    mock_display.flush.assert_called_once()


def test_send_incr_chunk_completion_sent_and_transfer_retained() -> None:
    """Test that after zero-length write, completion_sent is True and transfer retained."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    content = b"x" * 100

    # Set offset >= content length (triggers completion)
    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=100,
        start_time=0.0,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    send_incr_chunk(mock_display, state, transfer_key, pending_incr_sends)

    # Verify completion_sent is now True
    assert state.completion_sent is True

    # Verify transfer is still in pending_incr_sends (not removed yet)
    assert transfer_key in pending_incr_sends

    # Verify the state object is the same one
    assert pending_incr_sends[transfer_key] is state
