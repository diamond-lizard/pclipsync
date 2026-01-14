#!/usr/bin/env python3
"""Tests for INCR transfer cleanup with concurrent transfers."""
from unittest.mock import MagicMock


def test_unsubscribe_incr_requestor_concurrent_transfers() -> None:
    """Test cleanup with two concurrent transfers to same requestor."""
    from pclipsync.clipboard_selection import (
        unsubscribe_incr_requestor,
        IncrSendState,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    content = b"x" * 100

    # Two transfers to same requestor, different properties
    state1 = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=100,
        start_time=0.0,
        completion_sent=True,
    )
    state2 = IncrSendState(
        requestor=mock_requestor,
        property_atom=124,  # Different property
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=50,  # Not yet complete
        start_time=0.0,
        completion_sent=False,
    )

    transfer_key1 = (mock_requestor.id, 123)
    transfer_key2 = (mock_requestor.id, 124)
    pending_incr_sends = {transfer_key1: state1, transfer_key2: state2}

    # Cleanup first transfer
    unsubscribe_incr_requestor(mock_display, state1, transfer_key1, pending_incr_sends)

    # Verify first transfer was removed
    assert transfer_key1 not in pending_incr_sends
    assert transfer_key2 in pending_incr_sends
    assert len(pending_incr_sends) == 1

    # Verify change_attributes was NOT called (other transfer still exists)
    mock_requestor.change_attributes.assert_not_called()

    # Now cleanup second (last) transfer
    unsubscribe_incr_requestor(mock_display, state2, transfer_key2, pending_incr_sends)

    # Verify second transfer was removed
    assert transfer_key2 not in pending_incr_sends
    assert len(pending_incr_sends) == 0

    # Verify change_attributes WAS called (last transfer)
    mock_requestor.change_attributes.assert_called_once_with(event_mask=0)
