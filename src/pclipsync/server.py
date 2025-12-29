#!/usr/bin/env python3
"""Server mode implementation for pclipsync.

The server runs on the local machine (X) and listens on a Unix domain socket.
When an SSH tunnel establishes a connection from the remote client, the server:
- Monitors local CLIPBOARD and PRIMARY selections for changes
- Sends clipboard content to the connected client via netstring protocol
- Receives clipboard content from client and updates local selections
- Exits with code 0 when the client disconnects

The server accepts exactly one client connection. On startup, it checks if
the socket file exists and whether it belongs to an active server (refusing
to start) or is stale (unlinking and proceeding).

Usage:
    pclipsync --server --socket /path/to/socket
"""

from __future__ import annotations


async def run_server(socket_path: str) -> None:
    """Run the server, accepting one client and syncing clipboards.

    Validates X11 display, creates hidden window for clipboard ownership,
    registers for clipboard events, checks socket state, and starts listening.
    Accepts exactly one client connection and runs sync loop. Exits with
    code 0 on client disconnect.

    Args:
        socket_path: Path to the Unix domain socket to listen on.
    """
    import asyncio

    from pclipsync.clipboard import create_hidden_window, validate_display
    from pclipsync.clipboard_events import register_xfixes_events
    from pclipsync.hashing import HashState
    from pclipsync.server_handler import handle_client
    from pclipsync.server_socket import check_socket_state, print_startup_message
    from pclipsync.sync import ClipboardState


    # Initialize X11
    display = validate_display()
    window = create_hidden_window(display)
    register_xfixes_events(display, window)

    # Initialize state
    state = ClipboardState(
        display=display,
        window=window,
        hash_state=HashState(),
        current_content=b"",
    )

    # Check and prepare socket
    check_socket_state(socket_path)
    print_startup_message(socket_path)

    # Start server and accept one client
    shutdown_event = asyncio.Event()
    server = await asyncio.start_unix_server(
        lambda r, w: handle_client(state, r, w, shutdown_event),
        path=socket_path,
    )

    async with server:
        await shutdown_event.wait()
        server.close()
