#!/usr/bin/env python3
"""Tests for PropertyReadResult dataclass behavior."""
import pytest


class TestPropertyReadResult:
    """Tests for PropertyReadResult dataclass behavior."""

    def test_normal_content_result(self) -> None:
        """PropertyReadResult stores normal content correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=b"hello", is_incr=False)
        assert result.content == b"hello"
        assert result.is_incr is False
        assert result.estimated_size == 0

    def test_incr_result(self) -> None:
        """PropertyReadResult stores INCR detection correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=None, is_incr=True, estimated_size=1024)
        assert result.content is None
        assert result.is_incr is True
        assert result.estimated_size == 1024

    def test_failed_read_result(self) -> None:
        """PropertyReadResult represents failed read correctly."""
        from pclipsync.clipboard_io import PropertyReadResult

        result = PropertyReadResult(content=None, is_incr=False)
        assert result.content is None
        assert result.is_incr is False
        assert result.estimated_size == 0

    def test_equality(self) -> None:
        """PropertyReadResult instances are equal when fields match."""
        from pclipsync.clipboard_io import PropertyReadResult

        r1 = PropertyReadResult(content=b"test", is_incr=False)
        r2 = PropertyReadResult(content=b"test", is_incr=False)
        assert r1 == r2

        r3 = PropertyReadResult(content=b"other", is_incr=False)
        assert r1 != r3
