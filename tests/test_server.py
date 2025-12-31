#!/usr/bin/env python3
"""Tests for server mode implementation."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pclipsync.protocol import ProtocolError


@pytest.mark.asyncio
async def test_run_server_raises_exception_from_exception_holder() -> None:
    """Test run_server raises exception from exception_holder after shutdown."""

    error = ProtocolError("test error")

    # Mock all the X11 and socket setup at their source modules
    with patch("pclipsync.clipboard.validate_display") as mock_display, \
        patch("pclipsync.clipboard.create_hidden_window") as mock_window, \
        patch("pclipsync.clipboard_events.register_xfixes_events"), \
        patch("pclipsync.server_socket.check_socket_state"), \
        patch("pclipsync.server_socket.print_startup_message"), \
        patch("asyncio.start_unix_server") as mock_start_server:

        mock_display.return_value = MagicMock()
        mock_display.return_value.intern_atom.return_value = 1
        mock_window.return_value = MagicMock()

        # Create mock server context manager
        mock_server = AsyncMock()
        mock_server.close = MagicMock()
        mock_server.__aenter__ = AsyncMock(return_value=mock_server)
        mock_server.__aexit__ = AsyncMock(return_value=None)
        mock_start_server.return_value = mock_server

        async def simulate_client_error():
            # Wait for server to start
            await asyncio.sleep(0.02)
            # Get the lambda handler from call args
            handler = mock_start_server.call_args[0][0]
            # Mock reader/writer
            reader = AsyncMock()
            writer = AsyncMock()
            writer.close = MagicMock()
            writer.wait_closed = AsyncMock()
            # Call handler - it will populate exception_holder and set shutdown_event
            with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
                mock_sync.side_effect = error
                await handler(reader, writer)

        from pclipsync.server import run_server

        with pytest.raises(ProtocolError) as exc_info:
            task = asyncio.create_task(run_server("/tmp/test.sock"))
            await simulate_client_error()
            await task

        assert exc_info.value is error


@pytest.mark.asyncio
async def test_run_server_exits_cleanly_on_shutdown_before_client() -> None:
    """Test run_server exits cleanly when shutdown_requested before client connects."""

    # Mock all the X11 and socket setup at their source modules
    with patch("pclipsync.clipboard.validate_display") as mock_display, \
        patch("pclipsync.clipboard.create_hidden_window") as mock_window, \
        patch("pclipsync.clipboard_events.register_xfixes_events"), \
        patch("pclipsync.server_socket.check_socket_state"), \
        patch("pclipsync.server_socket.print_startup_message"), \
        patch("asyncio.start_unix_server") as mock_start_server:

        mock_display.return_value = MagicMock()
        mock_display.return_value.intern_atom.return_value = 1
        mock_window.return_value = MagicMock()

        # Create mock server context manager
        mock_server = AsyncMock()
        mock_server.close = MagicMock()
        mock_server.__aenter__ = AsyncMock(return_value=mock_server)
        mock_server.__aexit__ = AsyncMock(return_value=None)
        mock_start_server.return_value = mock_server

        # Patch signal handlers to capture shutdown_requested event
        shutdown_requested_ref = []

        original_add_signal_handler = asyncio.get_event_loop().add_signal_handler

        def capture_signal_handler(sig, callback):
            # Store the callback (which is shutdown_requested.set)
            shutdown_requested_ref.append(callback)

        with patch.object(
            asyncio.get_event_loop(), "add_signal_handler", side_effect=capture_signal_handler
        ):
            from pclipsync.server import run_server

            async def trigger_shutdown():
                await asyncio.sleep(0.02)
                # Simulate SIGINT by calling the captured handler
                if shutdown_requested_ref:
                    shutdown_requested_ref[0]()

            # Should complete without exception (no client connected)
            task = asyncio.create_task(run_server("/tmp/test.sock"))
            await trigger_shutdown()
            await asyncio.wait_for(task, timeout=1.0)
