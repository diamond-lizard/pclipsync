#!/usr/bin/env python3
"""Tests for client connection and retry logic."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

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
    return state


@pytest.mark.asyncio
async def test_connect_to_server_success() -> None:
    """Test connect_to_server returns reader/writer on success."""
    from pclipsync.client_retry import connect_to_server

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()

    with patch("asyncio.open_unix_connection", new_callable=AsyncMock) as mock_open:
        mock_open.return_value = (mock_reader, mock_writer)
        reader, writer = await connect_to_server("/tmp/test.sock")

        mock_open.assert_called_once_with("/tmp/test.sock")
        assert reader is mock_reader
        assert writer is mock_writer


@pytest.mark.asyncio
async def test_connect_to_server_failure_raises_connection_error() -> None:
    """Test connect_to_server raises ConnectionError on failure."""
    from pclipsync.client_retry import connect_to_server

    with patch("asyncio.open_unix_connection", new_callable=AsyncMock) as mock_open:
        mock_open.side_effect = OSError("Connection refused")

        with pytest.raises(ConnectionError) as exc_info:
            await connect_to_server("/tmp/test.sock")

        assert "Connection refused" in str(exc_info.value)


@pytest.mark.asyncio
async def test_run_client_connection_clears_hash_state(mock_state: MagicMock) -> None:
    """Test hash state is cleared on each connection attempt."""
    from pclipsync.client_retry import run_client_connection

    # Set up hash state with some values
    mock_state.hash_state.record_sent("abc123")
    mock_state.hash_state.record_received("def456")

    assert mock_state.hash_state.last_sent_hash is not None
    assert mock_state.hash_state.last_received_hash is not None

    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    mock_writer.close = MagicMock()
    mock_writer.wait_closed = AsyncMock()

    with patch("pclipsync.client_retry.connect_to_server", new_callable=AsyncMock) as mock_conn:
        mock_conn.return_value = (mock_reader, mock_writer)
        with patch("pclipsync.client_retry.run_sync_loop", new_callable=AsyncMock) as mock_sync:
            # Make sync loop raise to exit immediately
            mock_sync.side_effect = KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                await run_client_connection("/tmp/test.sock", mock_state)

    # Hash state should have been cleared
    assert mock_state.hash_state.last_sent_hash is None
    assert mock_state.hash_state.last_received_hash is None


