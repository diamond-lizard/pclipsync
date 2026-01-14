#!/usr/bin/env python3
"""Tests for sync_loop_inner shutdown and goodbye handling.

Tests that the sync loop returns cleanly on shutdown signals
and goodbye messages.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def make_slow_read(reader: asyncio.StreamReader) -> bytes:
    """Mock read that waits forever."""
    await asyncio.sleep(10)
    return b"never reached"


async def make_goodbye_read(reader: asyncio.StreamReader) -> bytes:
    """Mock read that returns empty bytes (goodbye message)."""
    return b""


def create_test_state() -> MagicMock:
    """Create a standard mock state for tests."""
    state = MagicMock()
    state.display = MagicMock()
    state.x11_event = asyncio.Event()
    state.pending_incr_sends = {}
    return state


async def trigger_shutdown_after_delay(shutdown_event: asyncio.Event) -> None:
    """Trigger shutdown event after a short delay."""
    await asyncio.sleep(0.01)
    shutdown_event.set()


@pytest.mark.asyncio
async def test_sync_loop_returns_cleanly_on_shutdown_requested() -> None:
    """Verify sync loop returns cleanly when shutdown_requested is set."""
    state = create_test_state()
    reader, writer = MagicMock(), AsyncMock()
    shutdown_requested = asyncio.Event()

    read_patch = patch("pclipsync.sync_loop_inner.read_netstring", make_slow_read)
    bye_patch = patch("pclipsync.sync_loop_inner.send_goodbye", AsyncMock())
    proc_patch = patch("pclipsync.sync_loop_inner.process_x11_events", AsyncMock())

    with read_patch, bye_patch as mock_goodbye, proc_patch:
        from pclipsync.sync_loop_inner import sync_loop_inner
        loop_coro = sync_loop_inner(state, reader, writer, shutdown_requested)
        task = asyncio.create_task(loop_coro)
        await trigger_shutdown_after_delay(shutdown_requested)
        await asyncio.wait_for(task, timeout=1.0)

    mock_goodbye.assert_called_once_with(writer)


@pytest.mark.asyncio
async def test_sync_loop_returns_cleanly_on_goodbye_received() -> None:
    """Verify sync loop returns cleanly when goodbye (empty content) is received."""
    state = create_test_state()
    reader, writer = MagicMock(), AsyncMock()
    shutdown_requested = asyncio.Event()

    read_patch = patch("pclipsync.sync_loop_inner.read_netstring", make_goodbye_read)
    proc_patch = patch("pclipsync.sync_loop_inner.process_x11_events", AsyncMock())

    with read_patch, proc_patch:
        from pclipsync.sync_loop_inner import sync_loop_inner
        loop_coro = sync_loop_inner(state, reader, writer, shutdown_requested)
        await asyncio.wait_for(loop_coro, timeout=1.0)
