"""CLI handling for pclipsync.

This module provides the command-line interface for pclipsync, handling
argument parsing via click, logging configuration, and dispatching to server or client mode based on
user-specified options.

Usage:
    pclipsync --server --socket PATH [--verbose]
    pclipsync --client --socket PATH [--verbose]
"""

import click
import sys

from pclipsync.main_options import MutuallyExclusiveOption
from pclipsync.main_logging import configure_logging



@click.command()
@click.option(
    "--server",
    is_flag=True,
    cls=MutuallyExclusiveOption,
    not_required_if=["client"],
    help="Run in server mode",
)
@click.option(
    "--client",
    is_flag=True,
    cls=MutuallyExclusiveOption,
    not_required_if=["server"],
    help="Run in client mode",
)
@click.option(
    "--socket",
    required=True,
    type=click.Path(),
    help="Unix domain socket path",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable DEBUG-level logging",
)
def main(server: bool, client: bool, socket: str, verbose: bool) -> None:
    """Synchronize X11 clipboard between machines over SSH-tunneled socket."""
    if not server and not client:
        raise click.UsageError("Either --server or --client must be specified")

    configure_logging(verbose)

    _run_mode(server, socket)


def _run_mode(server: bool, socket: str) -> None:
    """Run the appropriate mode (server or client).

    Args:
        server: True for server mode, False for client mode.
        socket: Path to the Unix domain socket.
    """
    import asyncio
    from pclipsync.client import run_client
    from pclipsync.protocol import ProtocolError

    try:
        if server:
            _run_server_with_cleanup(socket)
        else:
            asyncio.run(run_client(socket))
    except (ProtocolError, ConnectionError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _run_server_with_cleanup(socket: str) -> None:
    """Run server mode with socket cleanup on exit.

    Args:
        socket: Path to the Unix domain socket.
    """
    import asyncio
    from pclipsync.server import run_server
    from pclipsync.server_socket import cleanup_socket

    try:
        asyncio.run(run_server(socket))
    finally:
        cleanup_socket(socket)
