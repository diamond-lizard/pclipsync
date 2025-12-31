#!/usr/bin/env python3
"""Tests for server client connection handler."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncio

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
def mock_shutdown_event() -> MagicMock:
    """Create a mock shutdown event."""
    return MagicMock()

@pytest.mark.asyncio
async def test_handle_client_runs_sync_loop_and_signals_shutdown(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock
) -> None:
    """Test handle_client runs sync loop, cleans up, and signals shutdown."""
    from pclipsync.server_handler import handle_client

    reader = AsyncMock()
    shutdown_requested = asyncio.Event()
    exception_holder: list[Exception] = []

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        await handle_client(mock_state, reader, mock_writer, mock_shutdown_event, shutdown_requested, exception_holder)

        mock_sync.assert_called_once_with(mock_state, reader, mock_writer, shutdown_requested)
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        mock_shutdown_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_handles_protocol_error(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock
) -> None:
    """Test handle_client handles ProtocolError and still signals shutdown."""
    from pclipsync.protocol import ProtocolError
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ProtocolError("connection closed")
        await handle_client(mock_state, AsyncMock(), mock_writer, mock_shutdown_event, asyncio.Event(), [])
        mock_shutdown_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_handles_connection_error(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock
) -> None:
    """Test handle_client handles ConnectionError and still signals shutdown."""
    from pclipsync.server_handler import handle_client

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = ConnectionError("lost")
        await handle_client(mock_state, AsyncMock(), mock_writer, mock_shutdown_event, asyncio.Event(), [])
        mock_shutdown_event.set.assert_called_once()


@pytest.mark.asyncio
async def test_handle_client_stores_protocol_error_in_exception_holder(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test handle_client stores ProtocolError in exception_holder and logs ERROR."""
    import logging

    from pclipsync.protocol import ProtocolError
    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []
    error = ProtocolError("connection closed")

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = error
        with caplog.at_level(logging.ERROR):
            await handle_client(
                mock_state, AsyncMock(), mock_writer, mock_shutdown_event,
                asyncio.Event(), exception_holder
            )

    assert len(exception_holder) == 1
    assert exception_holder[0] is error
    assert "Protocol error" in caplog.text


@pytest.mark.asyncio
async def test_handle_client_stores_connection_error_in_exception_holder(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test handle_client stores ConnectionError in exception_holder and logs ERROR."""
    import logging

    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []
    error = ConnectionError("connection lost")

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync:
        mock_sync.side_effect = error
        with caplog.at_level(logging.ERROR):
            await handle_client(
                mock_state, AsyncMock(), mock_writer, mock_shutdown_event,
                asyncio.Event(), exception_holder
            )

    assert len(exception_holder) == 1
    assert exception_holder[0] is error
    assert "Connection error" in caplog.text


@pytest.mark.asyncio
async def test_handle_client_logs_debug_on_clean_disconnect(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test handle_client logs at DEBUG on normal return (goodbye received)."""
    import logging

    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []

    with patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock):
        with caplog.at_level(logging.DEBUG):
            await handle_client(
                mock_state, AsyncMock(), mock_writer, mock_shutdown_event,
                asyncio.Event(), exception_holder
            )

    assert len(exception_holder) == 0
    assert "Client disconnected cleanly" in caplog.text
