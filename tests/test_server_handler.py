#!/usr/bin/env python3
"""Tests for server client connection handler."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock ClipboardState."""
    state = MagicMock()
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.current_content = b""
    return state


@pytest.fixture
def mock_writer() -> AsyncMock:
    """Create a mock StreamWriter."""
    writer = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


@pytest.mark.asyncio
async def test_handle_client_runs_sync_loop_and_cleans_up(
    mock_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_client runs sync loop, cleans up socket, and exits 0."""
    from pclipsync.server_handler import handle_client

    socket_path = "/tmp/test.sock"
    reader = AsyncMock()

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        with patch("pclipsync.server_socket.cleanup_socket") as mock_cleanup:
            with pytest.raises(SystemExit) as exc_info:
                await handle_client(mock_state, reader, mock_writer, socket_path)

            mock_sync.assert_called_once_with(mock_state, reader, mock_writer)
            mock_cleanup.assert_called_once_with(socket_path)
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_called_once()
            assert exc_info.value.code == 0


@pytest.mark.asyncio
async def test_handle_client_handles_protocol_error(
    mock_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_client handles ProtocolError and still exits cleanly."""
    from pclipsync.protocol import ProtocolError
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ProtocolError("connection closed")
        with patch("pclipsync.server_socket.cleanup_socket"):
            with pytest.raises(SystemExit) as exc_info:
                await handle_client(mock_state, AsyncMock(), mock_writer, "/tmp/t.sock")
            assert exc_info.value.code == 0


@pytest.mark.asyncio
async def test_handle_client_handles_connection_error(
    mock_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_client handles ConnectionError and still exits cleanly."""
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ConnectionError("lost")
        with patch("pclipsync.server_socket.cleanup_socket"):
            with pytest.raises(SystemExit) as exc_info:
                await handle_client(mock_state, AsyncMock(), mock_writer, "/tmp/t.sock")
            assert exc_info.value.code == 0
