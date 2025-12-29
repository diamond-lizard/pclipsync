#!/usr/bin/env python3
"""Client connection and retry logic for pclipsync.

This module provides connection handling with automatic retry using
tenacity for exponential backoff. Used by the client module for
establishing and maintaining the connection to the server.
"""

from __future__ import annotations

import asyncio
import logging

from tenacity import retry, retry_if_exception_type, stop_never, wait_exponential

from pclipsync.client_constants import INITIAL_WAIT, MAX_WAIT, WAIT_MULTIPLIER
from pclipsync.sync import run_sync_loop
from pclipsync.sync_state import ClipboardState

logger = logging.getLogger(__name__)


async def connect_to_server(
    socket_path: str,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Connect to pclipsync server via Unix domain socket.

    Opens an asyncio Unix socket connection to the server at the
    specified path.

    Args:
        socket_path: Path to the Unix domain socket.

    Returns:
        Tuple of (StreamReader, StreamWriter) for the connection.

    Raises:
        ConnectionError: If connection fails (socket not found, refused, etc).
    """
    try:
        return await asyncio.open_unix_connection(socket_path)
    except OSError as e:
        raise ConnectionError(f"Failed to connect to {socket_path}: {e}") from e


@retry(
    wait=wait_exponential(
        multiplier=WAIT_MULTIPLIER,
        min=INITIAL_WAIT,
        max=MAX_WAIT,
    ),
    retry=retry_if_exception_type((ConnectionError, OSError)),
    stop=stop_never,
)
async def run_client_with_retry(
    socket_path: str,
    state: ClipboardState,
) -> None:
    """Connect to server with retry and run sync loop.

    Wraps connection and sync logic with tenacity retry decorator for
    automatic reconnection on connection failures. Clears hash state
    on each reconnect attempt for clean loop prevention tracking.

    Args:
        socket_path: Path to the Unix domain socket.
        state: The clipboard synchronization state.

    Note:
        This function never returns normally - it either runs forever
        or raises an exception that doesn't trigger retry.
    """
    # Clear hash state for clean slate on each connection attempt
    state.hash_state.clear()

    logger.debug("Connecting to server at %s", socket_path)
    try:
        reader, writer = await connect_to_server(socket_path)
    except ConnectionError:
        logger.warning("Connection to %s failed, will retry", socket_path)
        raise

    logger.debug("Connected to server at %s", socket_path)
    try:
        await run_sync_loop(state, reader, writer)
    except (ConnectionError, OSError) as e:
        logger.warning("Connection lost: %s, will retry", e)
        raise
    finally:
        writer.close()
        await writer.wait_closed()
