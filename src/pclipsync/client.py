#!/usr/bin/env python3
"""Client mode implementation for pclipsync.

This module implements client mode which connects to a pclipsync server
via an SSH-tunneled Unix domain socket. The client monitors the local
X11 clipboard and sends changes to the server, while also receiving
clipboard updates from the server.

Retry Strategy:
    The client uses tenacity for automatic reconnection with exponential
    backoff when the connection is lost. Parameters:
    - Initial wait: 1 second
    - Maximum wait: 60 seconds
    - Multiplier: 2x (exponential)
    - Unlimited retries

    On each reconnect, the hash state is cleared to ensure a clean slate
    for loop prevention tracking.
"""

from __future__ import annotations

import asyncio
import logging

from tenacity import retry, retry_if_exception_type, stop_never, wait_exponential

from pclipsync.sync import run_sync_loop
from pclipsync.sync_state import ClipboardState
from pclipsync.clipboard import create_hidden_window, validate_display
from pclipsync.clipboard_events import register_xfixes_events

# Retry parameters for exponential backoff reconnection.
# Initial delay between connection attempts in seconds.
INITIAL_WAIT: float = 1.0

# Maximum delay between connection attempts in seconds.
MAX_WAIT: float = 60.0

# Multiplier for exponential backoff (delay = initial * multiplier^attempt).
WAIT_MULTIPLIER: float = 2.0

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


async def run_client(socket_path: str) -> None:
    """Run client mode connecting to pclipsync server.

    Main entry point for client mode. Validates X11 connectivity,
    creates a hidden window for clipboard ownership, registers for
    XFixes selection events, and connects to the server with automatic
    retry on disconnection.

    Args:
        socket_path: Path to the Unix domain socket.
    """
    display = validate_display()
    window = create_hidden_window(display)
    register_xfixes_events(display, window)

    state = ClipboardState(
        display=display,
        window=window,
    )

    await run_client_with_retry(socket_path, state)
