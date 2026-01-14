#!/usr/bin/env python3
"""Tests for client exit behavior."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncio

from pclipsync.hashing import HashState
from pclipsync.sync_state import ClipboardState


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock ClipboardState with real HashState."""
    state = MagicMock(spec=ClipboardState)
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.current_content = b""
    state.pending_incr_sends = {}
    return state


@pytest.mark.asyncio
async def test_run_client_connection_exits_1_on_protocol_error(
    mock_state: MagicMock
) -> None:
    """Test run_client_connection exits with code 1 on ProtocolError."""
    from pclipsync.client_retry import run_client_connection
    from pclipsync.protocol import ProtocolError

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()
    shutdown_requested = asyncio.Event()

    with patch("pclipsync.client_retry.connect_to_server", new_callable=AsyncMock) as mock_conn, \
        patch("pclipsync.client_retry.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_conn.return_value = (mock_reader, mock_writer)
        mock_sync.side_effect = ProtocolError("connection closed")

        with pytest.raises(SystemExit) as exc_info:
            await run_client_connection("/tmp/test.sock", mock_state, shutdown_requested)

        assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_run_client_connection_exits_1_on_connection_error(
    mock_state: MagicMock
) -> None:
    """Test run_client_connection exits with code 1 on ConnectionError."""
    from pclipsync.client_retry import run_client_connection

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()
    shutdown_requested = asyncio.Event()

    with patch("pclipsync.client_retry.connect_to_server", new_callable=AsyncMock) as mock_conn, \
        patch("pclipsync.client_retry.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_conn.return_value = (mock_reader, mock_writer)
        mock_sync.side_effect = ConnectionError("connection lost")

        with pytest.raises(SystemExit) as exc_info:
            await run_client_connection("/tmp/test.sock", mock_state, shutdown_requested)

        assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_run_client_connection_exits_cleanly_on_goodbye(
    mock_state: MagicMock
) -> None:
    """Test run_client_connection exits cleanly when goodbye received."""
    from pclipsync.client_retry import run_client_connection

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()
    shutdown_requested = asyncio.Event()

    with patch("pclipsync.client_retry.connect_to_server", new_callable=AsyncMock) as mock_conn, \
        patch("pclipsync.client_retry.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_conn.return_value = (mock_reader, mock_writer)
        # Sync loop returns normally when goodbye received (no exception)
        mock_sync.return_value = None

        # Should complete without raising SystemExit or any exception
        await run_client_connection("/tmp/test.sock", mock_state, shutdown_requested)

    # Verify writer was cleaned up
    mock_writer.close.assert_called_once()
    mock_writer.wait_closed.assert_called_once()
