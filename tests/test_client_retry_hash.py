#!/usr/bin/env python3
"""Tests for hash state behavior in client retry logic."""
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
    shutdown_requested = asyncio.Event()

    with patch("pclipsync.client_retry.connect_to_server", new_callable=AsyncMock) as mock_conn, \
        patch("pclipsync.client_retry.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_conn.return_value = (mock_reader, mock_writer)
        # Make sync loop raise to exit immediately
        mock_sync.side_effect = KeyboardInterrupt()

        with pytest.raises(KeyboardInterrupt):
            await run_client_connection("/tmp/test.sock", mock_state, shutdown_requested)

    # Hash state should have been cleared
    assert mock_state.hash_state.last_sent_hash is None
    assert mock_state.hash_state.last_received_hash is None
