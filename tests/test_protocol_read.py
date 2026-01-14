#!/usr/bin/env python3
"""
Unit tests for netstring protocol reading (success cases).

Tests read_netstring function for valid inputs.
"""
import asyncio

import pytest

from pclipsync.protocol import (
    encode_netstring,
    read_netstring,
)


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
