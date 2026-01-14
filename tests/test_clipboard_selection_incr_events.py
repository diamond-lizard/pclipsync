#!/usr/bin/env python3
"""Tests for INCR send event routing (is_incr_send_event, handle_incr_send_event)."""
from unittest.mock import MagicMock


def test_property_delete_triggers_chunk_send() -> None:
    """Test PropertyNotify with PropertyDelete state triggers chunk send."""
    from pclipsync.clipboard_selection import (
        is_incr_send_event,
        handle_incr_send_event,
        IncrSendState,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    content = b"x" * 100000  # Large content
    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=content,
        offset=0,  # First chunk not yet sent
        start_time=0.0,
        completion_sent=False,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    # Create mock PropertyNotify event with PropertyDelete state
    mock_event = MagicMock()
    mock_event.type = 28  # PropertyNotify
    mock_event.state = 1  # PropertyDelete
    mock_event.window = mock_requestor
    mock_event.atom = 123

    # Check event is recognized
    is_match, event_type = is_incr_send_event(mock_event, pending_incr_sends)
    assert is_match is True
    assert event_type == "property_delete"

    # Handle the event
    handle_incr_send_event(mock_display, mock_event, event_type, pending_incr_sends)

    # Verify chunk was written (change_property called on requestor)
    mock_requestor.change_property.assert_called_once()
    # Verify offset was updated
    assert state.offset > 0


def test_property_new_value_ignored() -> None:
    """Test PropertyNotify with PropertyNewValue state is ignored."""
    from pclipsync.clipboard_selection import is_incr_send_event, IncrSendState

    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=b"test",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    # Create mock PropertyNotify event with PropertyNewValue state
    mock_event = MagicMock()
    mock_event.type = 28  # PropertyNotify
    mock_event.state = 0  # PropertyNewValue (not PropertyDelete)
    mock_event.window = mock_requestor
    mock_event.atom = 123

    # Check event is NOT recognized
    is_match, event_type = is_incr_send_event(mock_event, pending_incr_sends)
    assert is_match is False
    assert event_type is None


def test_property_delete_untracked_window_ignored() -> None:
    """Test PropertyNotify for untracked window is ignored."""
    from pclipsync.clipboard_selection import is_incr_send_event, IncrSendState

    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=b"test",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    # Create mock PropertyNotify from a different window
    mock_other_window = MagicMock()
    mock_other_window.id = 99999  # Different window ID

    mock_event = MagicMock()
    mock_event.type = 28  # PropertyNotify
    mock_event.state = 1  # PropertyDelete
    mock_event.window = mock_other_window
    mock_event.atom = 123

    # Check event is NOT recognized (window not tracked)
    is_match, event_type = is_incr_send_event(mock_event, pending_incr_sends)
    assert is_match is False
    assert event_type is None


def test_destroy_notify_triggers_cleanup() -> None:
    """Test DestroyNotify for tracked requestor window triggers cleanup."""
    from pclipsync.clipboard_selection import (
        is_incr_send_event,
        handle_incr_send_event,
        IncrSendState,
    )

    mock_display = MagicMock()
    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    state = IncrSendState(
        requestor=mock_requestor,
        property_atom=123,
        target_atom=456,
        selection_atom=789,
        content=b"test content",
        offset=0,
        start_time=0.0,
        completion_sent=False,
    )

    transfer_key = (mock_requestor.id, 123)
    pending_incr_sends = {transfer_key: state}

    # Create mock DestroyNotify event
    mock_event = MagicMock()
    mock_event.type = 17  # DestroyNotify
    mock_event.window = mock_requestor

    # Check event is recognized
    is_match, event_type = is_incr_send_event(mock_event, pending_incr_sends)
    assert is_match is True
    assert event_type == "destroy"

    # Handle the event
    handle_incr_send_event(mock_display, mock_event, event_type, pending_incr_sends)

    # Verify transfer was cleaned up
    assert transfer_key not in pending_incr_sends
    assert len(pending_incr_sends) == 0
