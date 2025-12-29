#!/usr/bin/env python3
"""Client mode implementation for pclipsync.

This module provides the main entry point for client mode which connects
to a pclipsync server via an SSH-tunneled Unix domain socket. The client
monitors the local X11 clipboard and sends changes to the server, while
also receiving clipboard updates from the server.

See client_retry.py for connection handling.
"""

from __future__ import annotations

from pclipsync.clipboard import create_hidden_window, validate_display
from pclipsync.clipboard_events import register_xfixes_events
from pclipsync.client_retry import run_client_connection
from pclipsync.sync_state import ClipboardState


async def run_client(socket_path: str) -> None:
    """Run client mode connecting to pclipsync server.

    Main entry point for client mode. Validates X11 connectivity,
    creates a hidden window for clipboard ownership, registers for
    XFixes selection events, and connects to the server.

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

    await run_client_connection(socket_path, state)
