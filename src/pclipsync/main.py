"""CLI handling for pclipsync.

This module provides the command-line interface for pclipsync, handling
argument parsing via click, logging configuration, signal handling for
graceful shutdown, and dispatching to server or client mode based on
user-specified options.

Usage:
    pclipsync --server --socket PATH [--verbose]
    pclipsync --client --socket PATH [--verbose]
"""

import click
import signal
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

    # Lazy import of heavy modules after argument validation for fast --help
    import asyncio

    from pclipsync.server import run_server
    from pclipsync.client import run_client

    def handle_signal(signum: int, frame) -> None:
        """Handle shutdown signal by raising SystemExit."""
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        if server:
            from pclipsync.server_socket import cleanup_socket
            try:
                asyncio.run(run_server(socket))
            finally:
                cleanup_socket(socket)
        else:
            asyncio.run(run_client(socket))
    except SystemExit:
        pass
