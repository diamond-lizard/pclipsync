#!/usr/bin/env python3
"""Tests for _handle_incr_transfer function - basic cases."""
from unittest.mock import MagicMock, patch

import pytest


def make_incr_mocks():
    """Create standard mock objects for INCR transfer tests."""
    mock_display = MagicMock()
    mock_window = MagicMock()
    return mock_display, mock_window


class TestHandleIncrTransfer:
    """Tests for _handle_incr_transfer function."""

    def test_successful_three_chunk_transfer(self) -> None:
        """Successful 3-chunk INCR transfer assembles buffer correctly."""
        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display, mock_window = make_incr_mocks()
        mock_event = MagicMock()
        chunks = [b"Hello", b" ", b"World", b""]
        deferred: list = []

        wait_patch = patch("pclipsync.selection_utils.wait_for_property_notify", return_value=mock_event)
        read_patch = patch("pclipsync.clipboard_io._read_chunk_property", side_effect=chunks)
        with wait_patch as mock_wait, read_patch as mock_read:
            result = _handle_incr_transfer(mock_display, mock_window, 123, deferred, 5.0)

        assert result == b"Hello World"
        assert mock_wait.call_count == 4
        assert mock_read.call_count == 4

    def test_immediate_zero_length_chunk(self) -> None:
        """INCR transfer with immediate zero-length chunk returns empty bytes."""
        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display, mock_window = make_incr_mocks()
        mock_event = MagicMock()
        deferred: list = []

        wait_patch = patch("pclipsync.selection_utils.wait_for_property_notify", return_value=mock_event)
        read_patch = patch("pclipsync.clipboard_io._read_chunk_property", side_effect=[b""])
        with wait_patch as mock_wait, read_patch:
            result = _handle_incr_transfer(mock_display, mock_window, 123, deferred, 5.0)

        assert result == b""
        assert mock_wait.call_count == 1

    def test_timeout_on_second_chunk(self) -> None:
        """INCR transfer times out on second chunk returns None."""
        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display, mock_window = make_incr_mocks()
        mock_event = MagicMock()
        deferred: list = []

        wait_patch = patch("pclipsync.selection_utils.wait_for_property_notify", side_effect=[mock_event, None])
        read_patch = patch("pclipsync.clipboard_io._read_chunk_property", side_effect=[b"Hello"])
        with wait_patch as mock_wait, read_patch:
            result = _handle_incr_transfer(mock_display, mock_window, 123, deferred, 5.0)

        assert result is None
        assert mock_wait.call_count == 2
