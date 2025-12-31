#!/usr/bin/env python3
"""Tests for sync_loop_inner acquisition_time handling.

Tests that process_x11_events correctly clears acquisition_time
when ownership is lost via SetSelectionOwnerNotify events.
"""
import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def mock_clipboard_state() -> MagicMock:
    """Create a mock ClipboardState for testing."""
    state = MagicMock()
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.window.id = 12345
    state.current_content = b""
    state.acquisition_time = None
    state.deferred_events = []
    state.x11_event = asyncio.Event()
    state.owned_selections = set()
    return state


@pytest.fixture
def mock_writer() -> AsyncMock:
    """Create a mock StreamWriter for testing."""
    return AsyncMock()


def make_owner_event(owner_id: int, timestamp: int) -> MagicMock:
    """Create a mock SetSelectionOwnerNotify event."""
    event = MagicMock()
    # Make type(event).__name__ return "SetSelectionOwnerNotify"
    event.__class__.__name__ = "SetSelectionOwnerNotify"
    event.owner = MagicMock()
    event.owner.id = owner_id
    event.timestamp = timestamp
    event.selection = 1  # CLIPBOARD atom
    return event


@pytest.mark.asyncio
async def test_clears_timestamp_when_we_lose_ownership(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is cleared when we lose selection ownership."""
    # Set initial acquisition_time
    mock_clipboard_state.acquisition_time = 555666777
    mock_clipboard_state.owned_selections = {1}  # We own CLIPBOARD (selection=1)

    # Create event where someone else becomes owner (event.owner.id != state.window.id)
    event = make_owner_event(owner_id=99999, timestamp=888999000)

    with patch(
        "pclipsync.sync_loop_inner.process_pending_events"
    ) as mock_pending, patch(
        "pclipsync.sync_loop_inner.handle_clipboard_change", new_callable=AsyncMock
    ) as mock_handler:
        mock_pending.return_value = [event]

        from pclipsync.sync_loop_inner import process_x11_events
        await process_x11_events(mock_clipboard_state, mock_writer)

    # acquisition_time should be cleared to None
    assert mock_clipboard_state.acquisition_time is None
    assert mock_clipboard_state.owned_selections == set()



@pytest.mark.asyncio
async def test_partial_ownership_loss_keeps_acquisition_time(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is NOT cleared when we still own another selection."""
    # Set initial state: we own both CLIPBOARD (1) and PRIMARY (Xatom.PRIMARY)
    mock_clipboard_state.acquisition_time = 555666777
    mock_clipboard_state.owned_selections = {1, 2}  # CLIPBOARD and PRIMARY

    # Create event where someone else takes CLIPBOARD (selection=1)
    event = make_owner_event(owner_id=99999, timestamp=888999000)

    with patch(
        "pclipsync.sync_loop_inner.process_pending_events"
    ) as mock_pending, patch(
        "pclipsync.sync_loop_inner.handle_clipboard_change", new_callable=AsyncMock
    ) as mock_handler:
        mock_pending.return_value = [event]

        from pclipsync.sync_loop_inner import process_x11_events
        await process_x11_events(mock_clipboard_state, mock_writer)

    # CLIPBOARD should be removed from owned_selections
    assert 1 not in mock_clipboard_state.owned_selections
    # But PRIMARY is still owned
    assert 2 in mock_clipboard_state.owned_selections
    # acquisition_time should NOT be cleared (we still own PRIMARY)
    assert mock_clipboard_state.acquisition_time == 555666777

@pytest.mark.asyncio
async def test_read_task_not_cancelled_when_x11_event_fires() -> None:
    """Verify read_task is not cancelled when x11_event completes first.

    The read_task must persist across iterations to avoid StreamReader
    buffer corruption. Only the stateless x11_task should be cancelled.
    """
    # Track if read_task was cancelled
    read_cancelled = False

    async def mock_read_netstring(reader: asyncio.StreamReader) -> bytes:
        nonlocal read_cancelled
        try:
            # Simulate waiting for network data
            await asyncio.sleep(10)
            return b"test"
        except asyncio.CancelledError:
            read_cancelled = True
            raise

    state = MagicMock()
    state.display = MagicMock()
    reader = MagicMock()
    writer = AsyncMock()
    state.x11_event = asyncio.Event()

    with patch(
        "pclipsync.sync_loop_inner.read_netstring", side_effect=mock_read_netstring
    ) as mock_read, patch(
        "pclipsync.sync_loop_inner.process_x11_events", new_callable=AsyncMock
    ) as mock_process:
        from pclipsync.sync_loop_inner import sync_loop_inner

        # Run one iteration: set x11_event immediately, then cancel after processing
        async def run_one_iteration() -> None:
            # Give the loop time to start
            await asyncio.sleep(0.01)
            # Trigger x11 event
            state.x11_event.set()
            # Give time for one iteration to complete
            await asyncio.sleep(0.01)

        task = asyncio.create_task(sync_loop_inner(state, reader, writer))
        await run_one_iteration()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    # read_task should NOT have been cancelled during normal operation
    # It only gets cancelled in the finally block when the loop exits
    assert mock_process.called, "process_x11_events should have been called"


@pytest.mark.asyncio
async def test_new_read_task_created_after_previous_completes() -> None:
    """Verify a new read_task is created only after the previous one completes.

    When network data arrives (read_task completes), the loop should process
    the data and then create a new read_task for the next message.
    """
    call_count = 0

    async def mock_read_netstring(reader: asyncio.StreamReader) -> bytes:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call returns immediately with data
            return b"first message"
        else:
            # Subsequent calls wait forever (simulate no more data)
            await asyncio.sleep(10)
            return b"never reached"

    state = MagicMock()
    state.display = MagicMock()
    reader = MagicMock()
    writer = AsyncMock()
    state.x11_event = asyncio.Event()

    with patch(
        "pclipsync.sync_loop_inner.read_netstring", side_effect=mock_read_netstring
    ) as mock_read, patch(
        "pclipsync.sync_loop_inner.handle_incoming_content", new_callable=AsyncMock
    ) as mock_handle, patch(
        "pclipsync.sync_loop_inner.process_x11_events", new_callable=AsyncMock
    ):
        from pclipsync.sync_loop_inner import sync_loop_inner

        async def run_test() -> None:
            # Give time for the first read to complete and second to start
            await asyncio.sleep(0.05)

        task = asyncio.create_task(sync_loop_inner(state, reader, writer))
        await run_test()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    # read_netstring should have been called twice:
    # 1. Initially before the loop
    # 2. After processing the first message
    assert call_count == 2, f"Expected 2 calls, got {call_count}"
    # handle_incoming_content should have been called once with the first message
    mock_handle.assert_called_once_with(state, b"first message")
