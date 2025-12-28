#!/usr/bin/env python3
"""Main synchronization event loop.

This module provides the run_sync_loop function that integrates X11
clipboard monitoring with asyncio network I/O for bidirectional
clipboard synchronization.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from Xlib import X

from pclipsync.clipboard import get_display_fd
from pclipsync.clipboard_selection import handle_selection_request, process_pending_events
from pclipsync.protocol import ProtocolError, read_netstring
from pclipsync.sync_handlers import handle_clipboard_change, handle_incoming_content

if TYPE_CHECKING:
    from pclipsync.sync_state import ClipboardState

logger = logging.getLogger(__name__)


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
        x11_event.set()

    loop.add_reader(display_fd, on_x11_readable)
    try:
        await _sync_loop_inner(state, reader, writer, x11_event)
    finally:
        loop.remove_reader(display_fd)


async def _sync_loop_inner(
    state: ClipboardState,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    x11_event: asyncio.Event,
) -> None:
    """Inner sync loop handling X11 and network events."""
    while True:
        # Wait for either X11 event or network data
        read_task = asyncio.create_task(read_netstring(reader))
        x11_task = asyncio.create_task(x11_event.wait())

        done, pending = await asyncio.wait(
            {read_task, x11_task}, return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if x11_task in done:
            x11_event.clear()
            await _process_x11_events(state, writer)

        if read_task in done:
            content = read_task.result()
            await handle_incoming_content(state, content)


async def _process_x11_events(
    state: ClipboardState, writer: asyncio.StreamWriter
) -> None:
    """Process pending X11 events."""
    events = process_pending_events(state.display)
    for event in events:
        if event.type == X.SelectionRequest:
            handle_selection_request(state.display, event, state.current_content)
        elif hasattr(event, "subcode"):
            # XFixesSelectionNotify event
            await handle_clipboard_change(state, writer, event.selection)
