#!/usr/bin/env python3
"""
Unit tests for netstring protocol reading error cases.

Tests ProtocolError behavior for invalid inputs.
"""
import asyncio

import pytest

from pclipsync.protocol import (
    ProtocolError,
    read_netstring,
)


def make_reader(data: bytes) -> asyncio.StreamReader:
    """Create a StreamReader with the given data for testing."""
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


@pytest.mark.asyncio
async def test_read_netstring_missing_colon() -> None:
    """Test ProtocolError raised for missing colon separator."""
    reader = make_reader(b"12Hello world!,")
    with pytest.raises(ProtocolError, match="Invalid character"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_missing_comma() -> None:
    """Test ProtocolError raised for missing comma terminator."""
    reader = make_reader(b"5:hello")
    with pytest.raises(ProtocolError, match="Expected comma"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_length_mismatch() -> None:
    """Test ProtocolError raised when length doesn't match content."""
    reader = make_reader(b"10:short,")
    with pytest.raises(ProtocolError):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_oversized_content() -> None:
    """Test ProtocolError raised for content exceeding size limit."""
    reader = make_reader(b"99999999:data,")
    with pytest.raises(ProtocolError, match="exceeds limit"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_non_digit_length() -> None:
    """Test ProtocolError raised for non-digit in length field."""
    reader = make_reader(b"12x:Hello,")
    with pytest.raises(ProtocolError, match="Invalid character"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_length_field_too_long() -> None:
    """Test ProtocolError raised when length field exceeds 8 digits."""
    reader = make_reader(b"123456789:data,")
    with pytest.raises(ProtocolError, match="exceeds maximum digits"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_connection_closed() -> None:
    """Test ProtocolError raised on connection closed mid-message."""
    reader = make_reader(b"")
    with pytest.raises(ProtocolError, match="Connection closed"):
        await read_netstring(reader)


@pytest.mark.asyncio
async def test_read_netstring_incomplete_read_raises_protocol_error() -> None:
    """Test ProtocolError raised when readexactly hits EOF mid-content."""
    # Feed 10 bytes length, but only 3 bytes of content (no terminator)
    reader = make_reader(b"10:abc")
    with pytest.raises(ProtocolError, match="Connection closed"):
        await read_netstring(reader)
