#!/usr/bin/env python3
"""Tests for server handler - exception storage and logging."""
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import logging

import pytest

from conftest_server_handler import (
    mock_state,
    mock_writer,
    mock_shutdown_event,
)

# Re-export fixtures for pytest discovery
__all__ = ["mock_state", "mock_writer", "mock_shutdown_event"]


@pytest.mark.asyncio
async def test_handle_client_stores_protocol_error_in_exception_holder(
    mock_state: MagicMock, mock_writer: AsyncMock, mock_shutdown_event: MagicMock,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test handle_client stores ProtocolError in exception_holder and logs ERROR."""
    from pclipsync.protocol import ProtocolError
    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []
    error = ProtocolError("connection closed")

    with (
        patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync,
        caplog.at_level(logging.ERROR),
    ):
        mock_sync.side_effect = error
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
    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []
    error = ConnectionError("connection lost")

    with (
        patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock) as mock_sync,
        caplog.at_level(logging.ERROR),
    ):
        mock_sync.side_effect = error
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
    from pclipsync.server_handler import handle_client

    exception_holder: list[Exception] = []

    with (
        patch("pclipsync.sync.run_sync_loop", new_callable=AsyncMock),
        caplog.at_level(logging.DEBUG),
    ):
        await handle_client(
            mock_state, AsyncMock(), mock_writer, mock_shutdown_event,
            asyncio.Event(), exception_holder
        )

    assert len(exception_holder) == 0
    assert "Client disconnected cleanly" in caplog.text
