#!/usr/bin/env python3
"""Integration tests for INCR send event handling in sync_loop_inner."""
from unittest.mock import MagicMock


def test_complete_incr_send_flow() -> None:
    """Test complete INCR send flow: initiation, chunks, completion."""
    from pclipsync.clipboard_selection import (
        initiate_incr_send,
        handle_incr_send_event,
        is_incr_send_event,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )

    mock_display = MagicMock()
    # Configure max_request_length to trigger INCR for our content
    mock_display.display.info.max_request_length = 65536

    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    # Create content larger than one chunk but requiring multiple chunks
    chunk_count = 3
    content = b"x" * (INCR_CHUNK_SIZE * chunk_count)

    # Create mock SelectionRequest event
    mock_event = MagicMock()
    mock_event.requestor = mock_requestor
    mock_event.property = 123
    mock_event.target = 456
    mock_event.selection = 789
    mock_event.time = 0

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 999

    # Step 1: Initiate INCR transfer
    initiate_incr_send(
        mock_display, mock_event, content, pending_incr_sends, incr_atom
    )

    # Verify transfer was created
    transfer_key = (mock_requestor.id, 123)
    assert transfer_key in pending_incr_sends
    state = pending_incr_sends[transfer_key]
    assert state.offset == 0
    assert state.completion_sent is False

    # Verify INCR type was written with content length
    # First change_property call should be INCR type with size
    incr_call = mock_requestor.change_property.call_args_list[0]
    assert incr_call[0][0] == 123  # property_atom
    assert incr_call[0][1] == incr_atom  # INCR type

    # Reset mocks for chunk tracking
    mock_requestor.reset_mock()
    mock_display.reset_mock()

    # Step 2: Simulate PropertyNotify (PropertyDelete) events for each chunk
    accumulated_data = b""
    chunks_sent = 0

    while not state.completion_sent:
        # Create PropertyNotify with PropertyDelete
        notify_event = MagicMock()
        notify_event.type = 28  # PropertyNotify
        notify_event.state = 1  # PropertyDelete
        notify_event.window = mock_requestor
        notify_event.atom = 123

        is_match, evt_type = is_incr_send_event(notify_event, pending_incr_sends)
        assert is_match is True

        # Handle the event (sends next chunk or completion)
        handle_incr_send_event(
            mock_display, notify_event, evt_type, pending_incr_sends
        )

        # Get the chunk that was written
        call = mock_requestor.change_property.call_args
        chunk_data = call[0][3]  # Fourth argument is data
        accumulated_data += chunk_data
        chunks_sent += 1

        mock_requestor.reset_mock()

        # Safety check to prevent infinite loop
        if chunks_sent > chunk_count + 5:
            raise AssertionError("Too many chunks sent")

    # Verify all content was accumulated before zero-length completion
    assert accumulated_data == content  # Last chunk is empty
    # Note: accumulated_data includes empty completion chunk
    assert chunks_sent == chunk_count + 1  # chunks + zero-length

    # Transfer should still exist (waiting for final ack)
    assert transfer_key in pending_incr_sends

    # Step 3: Final PropertyDelete ack
    final_event = MagicMock()
    final_event.type = 28  # PropertyNotify
    final_event.state = 1  # PropertyDelete
    final_event.window = mock_requestor
    final_event.atom = 123

    is_match, evt_type = is_incr_send_event(final_event, pending_incr_sends)
    handle_incr_send_event(
        mock_display, final_event, evt_type, pending_incr_sends
    )

    # Transfer should now be cleaned up
    assert transfer_key not in pending_incr_sends


def test_concurrent_incr_sends_to_two_requestors() -> None:
    """Test concurrent INCR sends to two different requestors complete correctly."""
    from pclipsync.clipboard_selection import (
        initiate_incr_send,
        handle_incr_send_event,
        is_incr_send_event,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )

    mock_display = MagicMock()
    mock_display.display.info.max_request_length = 65536

    # Create two different requestors
    mock_requestor1 = MagicMock()
    mock_requestor1.id = 11111
    mock_requestor2 = MagicMock()
    mock_requestor2.id = 22222

    # Content requiring 2 chunks each
    content1 = b"A" * (INCR_CHUNK_SIZE * 2)
    content2 = b"B" * (INCR_CHUNK_SIZE * 2)

    # Create SelectionRequest events for both
    mock_event1 = MagicMock()
    mock_event1.requestor = mock_requestor1
    mock_event1.property = 100
    mock_event1.target = 456
    mock_event1.selection = 789
    mock_event1.time = 0

    mock_event2 = MagicMock()
    mock_event2.requestor = mock_requestor2
    mock_event2.property = 200
    mock_event2.target = 456
    mock_event2.selection = 789
    mock_event2.time = 0

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 999

    # Initiate both transfers
    initiate_incr_send(
        mock_display, mock_event1, content1, pending_incr_sends, incr_atom
    )
    initiate_incr_send(
        mock_display, mock_event2, content2, pending_incr_sends, incr_atom
    )

    # Verify both transfers exist
    key1 = (mock_requestor1.id, 100)
    key2 = (mock_requestor2.id, 200)
    assert key1 in pending_incr_sends
    assert key2 in pending_incr_sends
    assert len(pending_incr_sends) == 2

    state1 = pending_incr_sends[key1]
    state2 = pending_incr_sends[key2]

    # Reset mocks
    mock_requestor1.reset_mock()
    mock_requestor2.reset_mock()

    # Helper to simulate PropertyDelete and collect chunk
    def send_chunk(requestor: MagicMock, prop_atom: int) -> bytes:
        notify = MagicMock()
        notify.type = 28  # PropertyNotify
        notify.state = 1  # PropertyDelete
        notify.window = requestor
        notify.atom = prop_atom

        is_match, evt_type = is_incr_send_event(notify, pending_incr_sends)
        assert is_match is True

        handle_incr_send_event(mock_display, notify, evt_type, pending_incr_sends)

        call = requestor.change_property.call_args
        chunk = call[0][3]
        requestor.reset_mock()
        return chunk

    # Interleave chunk sends: req1, req2, req1, req2, ...
    accumulated1 = b""
    accumulated2 = b""

    # First chunks
    accumulated1 += send_chunk(mock_requestor1, 100)
    accumulated2 += send_chunk(mock_requestor2, 200)

    # Second chunks
    accumulated1 += send_chunk(mock_requestor1, 100)
    accumulated2 += send_chunk(mock_requestor2, 200)

    # Completion chunks (zero-length)
    accumulated1 += send_chunk(mock_requestor1, 100)
    accumulated2 += send_chunk(mock_requestor2, 200)

    # Both should now have completion_sent=True
    assert state1.completion_sent is True
    assert state2.completion_sent is True

    # Verify content matches
    assert accumulated1 == content1
    assert accumulated2 == content2

    # Both transfers still exist (awaiting final ack)
    assert key1 in pending_incr_sends
    assert key2 in pending_incr_sends

    # Final acks
    # Final ack for requestor1 - triggers cleanup, no chunk written
    final_notify1 = MagicMock()
    final_notify1.type = 28
    final_notify1.state = 1
    final_notify1.window = mock_requestor1
    final_notify1.atom = 100
    is_match, evt_type = is_incr_send_event(final_notify1, pending_incr_sends)
    handle_incr_send_event(mock_display, final_notify1, evt_type, pending_incr_sends)

    # Final ack for requestor2 - triggers cleanup, no chunk written
    final_notify2 = MagicMock()
    final_notify2.type = 28
    final_notify2.state = 1
    final_notify2.window = mock_requestor2
    final_notify2.atom = 200
    is_match, evt_type = is_incr_send_event(final_notify2, pending_incr_sends)
    handle_incr_send_event(mock_display, final_notify2, evt_type, pending_incr_sends)

    # Both should be cleaned up
    assert key1 not in pending_incr_sends
    assert key2 not in pending_incr_sends
    assert len(pending_incr_sends) == 0


def test_small_content_selection_request_regression() -> None:
    """Test small content SelectionRequest uses direct property write (regression)."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
    )

    mock_display = MagicMock()
    # Set max_request_length high enough that small content won't trigger INCR
    mock_display.display.info.max_request_length = 65536

    mock_requestor = MagicMock()
    mock_requestor.id = 12345

    # Small content (well under INCR threshold)
    content = b"Hello, world!"

    # Create mock SelectionRequest event
    mock_event = MagicMock()
    mock_event.requestor = mock_requestor
    mock_event.property = 123
    mock_event.target = 456  # Assume UTF8_STRING
    mock_event.selection = 789
    mock_event.time = 0

    # Configure intern_atom to return known values for target matching
    def mock_intern(name: str) -> int:
        atoms = {
            "UTF8_STRING": 456,
            "STRING": 457,
            "TARGETS": 458,
            "TIMESTAMP": 459,
        }
        return atoms.get(name, 0)

    mock_display.intern_atom.side_effect = mock_intern

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 999
    acquisition_time = 12345

    # Call handle_selection_request
    handle_selection_request(
        mock_display,
        mock_event,
        content,
        acquisition_time,
        pending_incr_sends,
        incr_atom,
    )

    # Verify NO INCR transfer was created (small content uses direct path)
    assert len(pending_incr_sends) == 0

    # Verify content was written directly to requestor's property
    mock_requestor.change_property.assert_called_once()
    call = mock_requestor.change_property.call_args
    assert call[0][0] == 123  # property_atom
    assert call[0][1] == 456  # target_atom (UTF8_STRING)
    assert call[0][3] == content  # The actual content

    # Verify SelectionNotify was sent
    mock_requestor.send_event.assert_called_once()
