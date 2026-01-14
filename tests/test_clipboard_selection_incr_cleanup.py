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



def test_cleanup_stale_incr_sends_removes_timed_out_transfers() -> None:
    """Test that stale transfers exceeding timeout are cleaned up."""
    import time
    from pclipsync.clipboard_selection import (
        cleanup_stale_incr_sends,
        IncrSendState,
        INCR_SEND_TIMEOUT,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    # Create a transfer that started long ago (expired)
    expired_time = time.time() - INCR_SEND_TIMEOUT - 10.0
    expired_state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=b"expired content",
        offset=0,
        start_time=expired_time,
        completion_sent=False,
    )

    # Create a fresh transfer (not expired)
    mock_requestor2 = MagicMock()
    mock_requestor2.id = 67890
    fresh_state = IncrSendState(
        requestor=mock_requestor2,
        property_atom=456,
        target_atom=456,
        selection_atom=789,
        content=b"fresh content",
        offset=0,
        start_time=time.time(),  # Just started
        completion_sent=False,
    )

    expired_key = (mock_requestor.id, 123)
    fresh_key = (mock_requestor2.id, 456)
    pending_incr_sends = {
        expired_key: expired_state,
        fresh_key: fresh_state,
    }

    # Call cleanup
    cleanup_stale_incr_sends(mock_display, pending_incr_sends)

    # Expired transfer should be removed
    assert expired_key not in pending_incr_sends

    # Fresh transfer should remain
    assert fresh_key in pending_incr_sends

    # Unsubscribe should have been called for expired requestor
    mock_requestor.change_attributes.assert_called_once_with(event_mask=0)

    # Fresh requestor should not have been modified
    mock_requestor2.change_attributes.assert_not_called()


def test_cleanup_incr_sends_on_ownership_loss_clears_matching_transfers() -> None:
    """Test that ownership loss clears all pending transfers for that selection."""
    from pclipsync.clipboard_selection import (
        cleanup_incr_sends_on_ownership_loss,
        IncrSendState,
    )

    mock_display = MagicMock()

    # Create two transfers for selection 100 (CLIPBOARD)
    mock_requestor1 = MagicMock()
    mock_requestor1.id = 11111
    state1 = IncrSendState(
        requestor=mock_requestor1,
        property_atom=123,
        target_atom=456,
        selection_atom=100,  # CLIPBOARD
        content=b"content1",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    mock_requestor2 = MagicMock()
    mock_requestor2.id = 22222
    state2 = IncrSendState(
        requestor=mock_requestor2,
        property_atom=456,
        target_atom=456,
        selection_atom=100,  # CLIPBOARD - same selection
        content=b"content2",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    # Create one transfer for selection 200 (PRIMARY)
    mock_requestor3 = MagicMock()
    mock_requestor3.id = 33333
    state3 = IncrSendState(
        requestor=mock_requestor3,
        property_atom=789,
        target_atom=456,
        selection_atom=200,  # PRIMARY - different selection
        content=b"content3",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    key1 = (mock_requestor1.id, 123)
    key2 = (mock_requestor2.id, 456)
    key3 = (mock_requestor3.id, 789)
    pending_incr_sends = {key1: state1, key2: state2, key3: state3}

    # Lose ownership of selection 100 (CLIPBOARD)
    cleanup_incr_sends_on_ownership_loss(mock_display, 100, pending_incr_sends)

    # Transfers for selection 100 should be removed
    assert key1 not in pending_incr_sends
    assert key2 not in pending_incr_sends

    # Transfer for selection 200 should remain
    assert key3 in pending_incr_sends

    # Unsubscribe should have been called for both removed requestors
    mock_requestor1.change_attributes.assert_called_once_with(event_mask=0)
    mock_requestor2.change_attributes.assert_called_once_with(event_mask=0)

    # Remaining requestor should not have been modified
    mock_requestor3.change_attributes.assert_not_called()
