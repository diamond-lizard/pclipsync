#!/usr/bin/env python3
"""Server socket utilities for pclipsync.

This module provides utility functions for managing the Unix domain socket
used by the server, including:
- Checking socket state (active vs stale)
- Printing startup messages
- Socket cleanup on shutdown
"""

from __future__ import annotations

import os
import socket
import sys


def check_socket_state(socket_path: str) -> None:
    """Check socket file state and handle stale sockets.

    If the socket file exists, attempts to connect to determine if an active
    server is running. If connection is refused (stale socket), unlinks the
    file and returns. If connection succeeds (active server), exits with error.

    Args:
        socket_path: Path to the Unix domain socket file.

    Raises:
        SystemExit: If socket is in use by active server or on other errors.
    """
    if not os.path.exists(socket_path):
        return

    # Try to connect to check if socket is active
    test_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        test_socket.connect(socket_path)
        # Connection succeeded - active server exists
        test_socket.close()
        print(f"Error: Socket already in use by active server: {socket_path}",
            file=sys.stderr)
        sys.exit(1)
    except ConnectionRefusedError:
        # Stale socket - unlink and proceed
        os.unlink(socket_path)
    except OSError as e:
        print(f"Error: Cannot access socket {socket_path}: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        test_socket.close()


def print_startup_message(socket_path: str) -> None:
    """Print server startup message to stderr.

    Prints confirmation that the socket is ready and shows an example SSH
    forward command template for the user.

    Args:
        socket_path: Path to the Unix domain socket.
    """
    print(f"Listening on {socket_path}", file=sys.stderr)
    print(f"Example SSH forward: ssh -R REMOTE_SOCKET_PATH:{socket_path} user@host",
            file=sys.stderr)


def cleanup_socket(socket_path: str) -> None:
    """Remove socket file on cleanup.

    Unlinks the socket file if it exists. Called during graceful shutdown.
    Does not register signal handlers itself - main.py handles signal
    registration and calls this function.

    Args:
        socket_path: Path to the Unix domain socket file to remove.
    """
    try:
        os.unlink(socket_path)
    except OSError:
        pass  # Socket may already be removed
