#!/usr/bin/env python3
"""Tests for INCR transfer detection."""
from unittest.mock import MagicMock


def test_needs_incr_transfer_false_for_small_content() -> None:
    """Test needs_incr_transfer returns False for content under threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer

    mock_display = MagicMock()
    # Set max_request_length to 65536 (256KB max property size)
    mock_display.info.max_request_length = 65536

    # Small content should not need INCR
    small_content = b"Hello, World!"
    assert needs_incr_transfer(small_content, mock_display) is False


def test_needs_incr_transfer_true_for_large_content() -> None:
    """Test needs_incr_transfer returns True for content exceeding threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer, INCR_SAFETY_MARGIN

    mock_display = MagicMock()
    # Set max_request_length to 1000 (4000 bytes max, ~3600 with safety margin)
    mock_display.info.max_request_length = 1000

    # Calculate threshold (1000 * 4 * 0.9 = 3600)
    threshold = int(1000 * 4 * INCR_SAFETY_MARGIN)

    # Content exceeding threshold should need INCR
    large_content = b"x" * (threshold + 1)
    assert needs_incr_transfer(large_content, mock_display) is True


def test_handle_selection_request_small_content_uses_direct_change_property() -> None:
    """Test that small content uses direct change_property, not INCR."""
    from pclipsync.clipboard_selection import handle_selection_request, IncrSendState

    mock_display = MagicMock()
    # Set max_request_length high enough that content is "small"
    mock_display.info.max_request_length = 65536  # 256KB max

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


def test_handle_selection_request_large_content_initiates_incr() -> None:
    """Test that large content initiates INCR transfer and creates pending entry."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.info.max_request_length = 100  # 400 bytes max, ~360 with margin

    mock_event = MagicMock()
    mock_event.requestor = MagicMock()
    mock_event.requestor.id = 12345
    mock_event.property = 123
    mock_event.selection = 456
    mock_event.time = 789

    # Make intern_atom return different values for different atoms
    def intern_atom_side_effect(name: str) -> int:
        atoms = {"TARGETS": 1, "UTF8_STRING": 2, "TIMESTAMP": 3}
        return atoms.get(name, 99)

    mock_display.intern_atom.side_effect = intern_atom_side_effect
    mock_event.target = 2  # UTF8_STRING

    # Large content exceeding threshold
    threshold = int(100 * 4 * INCR_SAFETY_MARGIN)
    large_content = b"x" * (threshold + 100)

    pending_incr_sends: dict[tuple[int, int], IncrSendState] = {}
    incr_atom = 100

    handle_selection_request(
        mock_display,
        mock_event,
        large_content,
        acquisition_time=1000,
        pending_incr_sends=pending_incr_sends,
        incr_atom=incr_atom,
    )

    # Verify INCR transfer was initiated - pending entry created
    transfer_key = (mock_event.requestor.id, mock_event.property)
    assert transfer_key in pending_incr_sends

    # Verify the IncrSendState was set up correctly
    state = pending_incr_sends[transfer_key]
    assert state.requestor == mock_event.requestor
    assert state.property_atom == mock_event.property
    assert state.target_atom == 2  # UTF8_STRING
    assert state.selection_atom == mock_event.selection
    assert state.content == large_content
    assert state.offset == 0
    assert state.completion_sent is False


def test_incr_response_has_correct_type_and_size() -> None:
    """Test INCR response writes INCR type with content length as value."""
    from pclipsync.clipboard_selection import (
        handle_selection_request,
        IncrSendState,
        INCR_SAFETY_MARGIN,
    )

    mock_display = MagicMock()
    # Set max_request_length low so content exceeds threshold
    mock_display.info.max_request_length = 100

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


def test_send_incr_chunk_first_chunk() -> None:
    """Test send_incr_chunk sends correct first chunk from offset 0."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )
    from unittest.mock import MagicMock

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


def test_send_incr_chunk_subsequent_chunk() -> None:
    """Test send_incr_chunk sends correct subsequent chunk with offset."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )
    from unittest.mock import MagicMock

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


def test_send_incr_chunk_zero_length_completion() -> None:
    """Test send_incr_chunk sends zero-length chunk when all content sent."""
    from pclipsync.clipboard_selection import (
        send_incr_chunk,
        IncrSendState,
        INCR_CHUNK_SIZE,
    )
    from unittest.mock import MagicMock

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
    from unittest.mock import MagicMock

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


def test_unsubscribe_incr_requestor_removes_transfer_and_unsubscribes() -> None:
    """Test cleanup removes transfer and unsubscribes when last for window."""
    from pclipsync.clipboard_selection import (
        unsubscribe_incr_requestor,
        IncrSendState,
    )
    from unittest.mock import MagicMock

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


def test_unsubscribe_incr_requestor_concurrent_transfers() -> None:
    """Test cleanup with two concurrent transfers to same requestor."""
    from pclipsync.clipboard_selection import (
        unsubscribe_incr_requestor,
        IncrSendState,
    )
    from unittest.mock import MagicMock

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
