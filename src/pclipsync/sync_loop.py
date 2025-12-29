#!/usr/bin/env python3
"""Main synchronization event loop.

This module provides the run_sync_loop function that integrates X11
clipboard monitoring with asyncio network I/O for bidirectional
clipboard synchronization.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from pclipsync.clipboard import get_display_fd
from pclipsync.sync_loop_inner import sync_loop_inner

if TYPE_CHECKING:
    from pclipsync.sync_state import ClipboardState



async def run_sync_loop(
    state: ClipboardState,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
) -> None:
    """Run the main synchronization event loop.

    Integrates X11 display file descriptor into asyncio event loop using
    add_reader(). Concurrently handles X11 clipboard events and incoming
    network data for bidirectional clipboard synchronization.

    Args:
        state: The clipboard synchronization state.
        reader: The asyncio StreamReader for the socket connection.
        writer: The asyncio StreamWriter for the socket connection.

    Raises:
        ProtocolError: On protocol violation from remote.
        ConnectionError: On connection loss.
    """
    loop = asyncio.get_event_loop()
    display_fd = get_display_fd(state.display)
    x11_event = asyncio.Event()

    def on_x11_readable() -> None:
        """Signal that X11 events are ready to be processed."""
        x11_event.set()

    loop.add_reader(display_fd, on_x11_readable)
    try:
        await sync_loop_inner(state, reader, writer, x11_event)
    finally:
        loop.remove_reader(display_fd)

