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


@pytest.fixture
def mock_server() -> MagicMock:
    """Create a mock asyncio Server."""
    return MagicMock()

@pytest.mark.asyncio
async def test_handle_client_runs_sync_loop_and_closes_server(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_server: MagicMock
) -> None:
    """Test handle_client runs sync loop, cleans up, and closes server."""
    from pclipsync.server_handler import handle_client

    reader = AsyncMock()

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        await handle_client(mock_state, reader, mock_writer, mock_server)

        mock_sync.assert_called_once_with(mock_state, reader, mock_writer)
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        mock_server.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_handles_protocol_error(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_server: MagicMock
) -> None:
    """Test handle_client handles ProtocolError and still closes server."""
    from pclipsync.protocol import ProtocolError
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ProtocolError("connection closed")
        await handle_client(mock_state, AsyncMock(), mock_writer, mock_server)
        mock_server.close.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_handles_connection_error(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_server: MagicMock
) -> None:
    """Test handle_client handles ConnectionError and still closes server."""
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ConnectionError("lost")
        await handle_client(mock_state, AsyncMock(), mock_writer, mock_server)
        mock_server.close.assert_called_once()
