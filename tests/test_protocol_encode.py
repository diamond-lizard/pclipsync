#!/usr/bin/env python3
"""
Unit tests for netstring protocol encoding and validation.

Tests encode_netstring and validate_content_size functions.
"""
import pytest

from pclipsync.protocol import (
    MAX_CONTENT_SIZE,
    encode_netstring,
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
