#!/usr/bin/env python3
"""Tests for sync_loop_inner read_task lifecycle management.

Tests that the read_task is properly managed to avoid StreamReader
buffer corruption from premature cancellation.
"""
import asyncio
from contextlib import suppress
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Module-level counter for counting read mock
_read_count = 0


async def make_slow_read(reader: asyncio.StreamReader) -> bytes:
    """Mock read that waits forever."""
    await asyncio.sleep(10)
    return b"test"


async def counting_read(reader: asyncio.StreamReader) -> bytes:
    """Mock read that counts calls. Returns data on first call only."""
    global _read_count
    _read_count += 1
    if _read_count == 1:
        return b"first message"
    await asyncio.sleep(10)
    return b"never reached"


def reset_read_count() -> None:
    """Reset the global read counter."""
    global _read_count
    _read_count = 0


def get_read_count() -> int:
    """Get the current read count."""
    return _read_count


def create_test_state() -> MagicMock:
    """Create a standard mock state for tests."""
    state = MagicMock()
    state.display = MagicMock()
    state.x11_event = asyncio.Event()
    state.pending_incr_sends = {}
    return state


async def cancel_task_safely(task: asyncio.Task[None]) -> None:
    """Cancel a task and suppress CancelledError."""
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_read_task_not_cancelled_when_x11_event_fires() -> None:
    """Verify read_task is not cancelled when x11_event completes first."""
    state = create_test_state()
    reader, writer = MagicMock(), AsyncMock()
    shutdown_requested = asyncio.Event()

    patches = patch("pclipsync.sync_loop_inner.read_netstring", make_slow_read)
    proc_patch = patch("pclipsync.sync_loop_inner.process_x11_events", AsyncMock())

    with patches, proc_patch as mock_process:
        from pclipsync.sync_loop_inner import sync_loop_inner
        task = asyncio.create_task(sync_loop_inner(state, reader, writer, shutdown_requested))
        await asyncio.sleep(0.01)
        state.x11_event.set()
        await asyncio.sleep(0.01)
        await cancel_task_safely(task)

    assert mock_process.called, "process_x11_events should have been called"


@pytest.mark.asyncio
async def test_new_read_task_created_after_previous_completes() -> None:
    """Verify a new read_task is created after the previous one completes."""
    reset_read_count()
    state = create_test_state()
    reader, writer = MagicMock(), AsyncMock()
    shutdown_requested = asyncio.Event()

    read_patch = patch("pclipsync.sync_loop_inner.read_netstring", counting_read)
    handle_patch = patch("pclipsync.sync_loop_inner.handle_incoming_content", AsyncMock())
    proc_patch = patch("pclipsync.sync_loop_inner.process_x11_events", AsyncMock())

    with read_patch, handle_patch as mock_handle, proc_patch:
        from pclipsync.sync_loop_inner import sync_loop_inner
        task = asyncio.create_task(sync_loop_inner(state, reader, writer, shutdown_requested))
        await asyncio.sleep(0.05)
        await cancel_task_safely(task)

    assert get_read_count() == 2, f"Expected 2 calls, got {get_read_count()}"
    mock_handle.assert_called_once_with(state, b"first message")
