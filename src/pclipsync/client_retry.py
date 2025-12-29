#!/usr/bin/env python3
"""Client connection logic for pclipsync.

This module provides connection handling for the client. When connection
fails, the client exits immediately with a helpful error message explaining
possible causes and remediation steps.
"""

from __future__ import annotations

import asyncio
import sys

from pclipsync.sync import run_sync_loop
from pclipsync.sync_state import ClipboardState


STALE_SOCKET_MESSAGE = """
Connection to {socket_path} failed.

Possible causes:
- The SSH tunnel is not established or has disconnected
- The pclipsync server is not running on the local machine
- A stale socket file exists from a previous SSH session

If the SSH tunnel and pclipsync server are both running, a stale socket
file may be preventing connection. To fix this:

1. Remove the stale socket file on the remote machine:
   rm -f {socket_path}

2. Re-establish the SSH tunnel (if needed)

3. Restart the pclipsync client

To prevent stale socket issues, add this to /etc/ssh/sshd_config on the
remote machine and restart sshd:
   StreamLocalBindUnlink yes
""".strip()


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


async def run_client_connection(
    socket_path: str,
    state: ClipboardState,
) -> None:
    """Connect to server and run sync loop.

    Attempts to connect to the server once. If connection fails, prints
    a helpful error message to stderr and exits with code 1. If connected,
    runs the sync loop until disconnection or error.

    Args:
        socket_path: Path to the Unix domain socket.
        state: The clipboard synchronization state.

    Note:
        On connection failure, this function calls sys.exit(1) and does
        not return.
    """
    state.hash_state.clear()

    try:
        reader, writer = await connect_to_server(socket_path)
    except ConnectionError:
        print(STALE_SOCKET_MESSAGE.format(socket_path=socket_path), file=sys.stderr)
        sys.exit(1)

    try:
        await run_sync_loop(state, reader, writer)
    finally:
        writer.close()
        await writer.wait_closed()
