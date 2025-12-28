#!/usr/bin/env python3
"""
Unit tests for netstring protocol encoding and decoding.

Tests encode_netstring, read_netstring, and ProtocolError behavior.
"""
import asyncio

import pytest

from pclipsync.protocol import (
    MAX_CONTENT_SIZE,
    ProtocolError,
    encode_netstring,
    read_netstring,
    validate_content_size,
)


def test_encode_netstring_produces_correct_format() -> None:
    """Test that encode_netstring produces correct netstring format."""
    result = encode_netstring(b"Hello world!")
    assert result == b"12:Hello world!,"


def test_encode_netstring_empty_content() -> None:
    """Test encoding empty content produces valid netstring."""
    result = encode_netstring(b"")
    assert result == b"0:,"


def test_encode_netstring_binary_content() -> None:
    """Test encoding binary data with null bytes."""
    data = b"\x00\x01\x02\xff"
    result = encode_netstring(data)
    assert result == b"4:\x00\x01\x02\xff,"


def test_validate_content_size_within_limit() -> None:
    """Test content within limit returns True."""
    data = b"x" * 1000
    assert validate_content_size(data) is True


def test_validate_content_size_at_limit() -> None:
    """Test content exactly at limit returns True."""
    data = b"x" * MAX_CONTENT_SIZE
    assert validate_content_size(data) is True


def test_validate_content_size_over_limit() -> None:
    """Test content over limit returns False."""
    data = b"x" * (MAX_CONTENT_SIZE + 1)
    assert validate_content_size(data) is False


def make_reader(data: bytes) -> asyncio.StreamReader:
    """Create a StreamReader with the given data for testing."""
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


@pytest.mark.asyncio
async def test_read_netstring_valid() -> None:
    """Test reading a valid netstring."""
    reader = make_reader(b"12:Hello world!,")
    result = await read_netstring(reader)
    assert result == b"Hello world!"


@pytest.mark.asyncio
async def test_read_netstring_empty_content() -> None:
    """Test reading netstring with empty content."""
    reader = make_reader(b"0:,")
    result = await read_netstring(reader)
    assert result == b""


@pytest.mark.asyncio
async def test_round_trip_encode_decode() -> None:
    """Test that encoding then decoding returns original data."""
    original = b"Test content with unicode: \xc3\xa9\xc3\xa0"
    encoded = encode_netstring(original)
    reader = make_reader(encoded)
    result = await read_netstring(reader)
    assert result == original


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
    with pytest.raises(asyncio.IncompleteReadError):
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
