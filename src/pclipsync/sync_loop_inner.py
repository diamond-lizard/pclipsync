#!/usr/bin/env python3
"""Inner synchronization loop implementation.

This module contains the inner event loop functions that handle X11 and
network events for bidirectional clipboard synchronization.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import TYPE_CHECKING, cast

from Xlib import X

from pclipsync.clipboard_selection import handle_selection_request, process_pending_events
from pclipsync.protocol import read_netstring, send_goodbye, is_goodbye
from pclipsync.sync_handlers import handle_clipboard_change, handle_incoming_content

if TYPE_CHECKING:
    from Xlib.protocol.event import SelectionRequest

    from pclipsync.sync_state import ClipboardState


async def sync_loop_inner(
    state: ClipboardState,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    shutdown_requested: asyncio.Event
) -> None:
    """Inner sync loop handling X11 and network events.

    Waits for either X11 events or network data and processes them
    appropriately for bidirectional clipboard synchronization.

    Args:
        state: The clipboard synchronization state.
        reader: The asyncio StreamReader for the socket connection.
        writer: The asyncio StreamWriter for the socket connection.
        shutdown_requested: Event signaling graceful shutdown request.
    """
    read_task = asyncio.create_task(read_netstring(reader))
    shutdown_task = asyncio.create_task(shutdown_requested.wait())
    try:
        while True:
            # Wait for either X11 event or network data
            x11_task = asyncio.create_task(state.x11_event.wait())

            done, pending = await asyncio.wait(
                {read_task, x11_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
            )

            # Only cancel x11_task - it's stateless (Event.wait)
            # Never cancel read_task - it would corrupt StreamReader buffer
            with suppress(asyncio.CancelledError):
                x11_task.cancel()
                await x11_task

            if x11_task in done:
                state.x11_event.clear()
                await process_x11_events(state, writer)

            if read_task in done:
                content = read_task.result()
                if is_goodbye(content):
                    logging.debug("Remote disconnected cleanly")
                    return
                await handle_incoming_content(state, content)
                read_task = asyncio.create_task(read_netstring(reader))

            if shutdown_task in done:
                await send_goodbye(writer)
                return

    finally:
        # Clean up read_task on loop exit
        read_task.cancel()
        with suppress(asyncio.CancelledError):
            await read_task
        shutdown_task.cancel()
        with suppress(asyncio.CancelledError):
            await shutdown_task

async def process_x11_events(
    state: ClipboardState, writer: asyncio.StreamWriter
) -> None:
    """Process pending X11 events.

    Handles SelectionRequest events (to serve clipboard content) and
    XFixesSelectionNotify events (to sync clipboard changes).

    Args:
        state: The clipboard synchronization state.
        writer: The asyncio StreamWriter for the socket connection.
    """
    events = process_pending_events(state.display, state.deferred_events)
    for event in events:
        if event.type == X.SelectionRequest:
            sel_event = cast("SelectionRequest", event)
            handle_selection_request(state.display, sel_event, state.current_content, state.acquisition_time)
        elif type(event).__name__ == "SetSelectionOwnerNotify":
            # XFixes SetSelectionOwnerNotify event - track ownership loss
            logging.debug("SetSelectionOwnerNotify: selection=%s owner=%s us=%s",
                event.selection, event.owner.id, state.window.id)
            if event.owner.id != state.window.id:
                # We lost ownership of this selection
                state.owned_selections.discard(event.selection)
                # Clear received hash: content from another app is not echo
                state.hash_state.clear_received_hash()
                # Clear sent hash: content from another app is not duplicate
                state.hash_state.clear_sent_hash()
                # Clear acquisition_time only when we own no selections
                if not state.owned_selections:
                    state.acquisition_time = None
            await handle_clipboard_change(state, writer, event.selection)
