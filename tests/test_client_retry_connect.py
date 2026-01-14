#!/usr/bin/env python3
"""Tests for client connection functions."""
from unittest.mock import AsyncMock, patch

import pytest


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
