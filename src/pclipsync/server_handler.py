#!/usr/bin/env python3
"""Server client connection handler.

This module provides the handler for client connections to the server.
When a client connects via the Unix domain socket, this handler runs
the synchronization loop and manages the connection lifecycle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio

    from pclipsync.sync_state import ClipboardState


async def handle_client(
    state: ClipboardState,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    shutdown_event: asyncio.Event,
    shutdown_requested: asyncio.Event,
    exception_holder: list[Exception],
) -> None:
    """Handle a single client connection.

    Runs the sync loop for bidirectional clipboard synchronization with
    the connected client. On disconnect (EOF, protocol error, or connection
    error), cleans up and closes the server.

    Args:
        state: The clipboard synchronization state.
        reader: The asyncio StreamReader for the socket connection.
        writer: The asyncio StreamWriter for the socket connection.
        shutdown_event: Event to set when client disconnects.
        shutdown_requested: Event signaling graceful shutdown request.
        exception_holder: List to store exceptions for propagation.
    """
    import logging

    from pclipsync.protocol import ProtocolError
    from pclipsync.sync import run_sync_loop

    logger = logging.getLogger(__name__)
    logger.debug("Client connected")

    try:
        await run_sync_loop(state, reader, writer, shutdown_requested)
        logger.debug("Client disconnected cleanly")
    except ProtocolError as e:
        logger.error("Protocol error: %s", e)
        exception_holder.append(e)
    except ConnectionError as e:
        logger.error("Connection error: %s", e)
        exception_holder.append(e)
    finally:
        writer.close()
        await writer.wait_closed()
        shutdown_event.set()
