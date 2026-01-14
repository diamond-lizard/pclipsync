#!/usr/bin/env python3
"""
Unit tests for goodbye protocol handling.

Tests is_goodbye and send_goodbye functions.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from pclipsync.protocol import (
    is_goodbye,
    send_goodbye,
)


def test_is_goodbye_empty_bytes() -> None:
    """Test is_goodbye returns True for empty bytes."""
    assert is_goodbye(b"") is True


def test_is_goodbye_non_empty_bytes() -> None:
    """Test is_goodbye returns False for non-empty bytes."""
    assert is_goodbye(b"hello") is False


@pytest.mark.asyncio
async def test_send_goodbye_writes_empty_netstring() -> None:
    """Test send_goodbye writes the goodbye message (empty netstring)."""
    writer = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    await send_goodbye(writer)
    writer.write.assert_called_once_with(b"0:,")
    writer.drain.assert_called_once()


@pytest.mark.asyncio
async def test_send_goodbye_ignores_os_error() -> None:
    """Test send_goodbye catches and ignores OSError (write errors)."""
    writer = AsyncMock()
    writer.write = MagicMock(side_effect=OSError("Connection reset"))
    # Should not raise
    await send_goodbye(writer)


@pytest.mark.asyncio
async def test_send_goodbye_ignores_timeout_error() -> None:
    """Test send_goodbye catches and ignores asyncio.TimeoutError."""
    writer = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock(side_effect=asyncio.TimeoutError())
    # Should not raise
    await send_goodbye(writer)
