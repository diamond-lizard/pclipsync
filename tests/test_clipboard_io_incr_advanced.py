#!/usr/bin/env python3
"""Tests for _handle_incr_transfer - advanced cases and INCR integration."""
from unittest.mock import MagicMock, patch

import pytest


def make_incr_mocks():
    """Create standard mock objects for INCR transfer tests."""
    mock_display = MagicMock()
    mock_window = MagicMock()
    return mock_display, mock_window


class TestHandleIncrTransferAdvanced:
    """Advanced tests for _handle_incr_transfer function."""

    def test_exceeds_max_content_size(self) -> None:
        """INCR transfer exceeding MAX_CONTENT_SIZE returns None."""
        from pclipsync.clipboard_io import _handle_incr_transfer
        from pclipsync.protocol import MAX_CONTENT_SIZE

        mock_display, mock_window = make_incr_mocks()
        mock_event = MagicMock()
        deferred: list = []

        chunk_size = (MAX_CONTENT_SIZE // 2) + 1
        large_chunk = b"x" * chunk_size
        chunks = [large_chunk, large_chunk]

        wait_patch = patch("pclipsync.selection_utils.wait_for_property_notify", return_value=mock_event)
        read_patch = patch("pclipsync.clipboard_io._read_chunk_property", side_effect=chunks)
        with wait_patch, read_patch:
            result = _handle_incr_transfer(mock_display, mock_window, 123, deferred, 5.0)

        assert result is None

    def test_deferred_events_accumulate_selection_requests(self) -> None:
        """INCR transfer defers SelectionRequest events to deferred_events list."""
        from pclipsync.clipboard_io import _handle_incr_transfer

        mock_display, mock_window = make_incr_mocks()
        mock_event = MagicMock()
        deferred: list = []

        mock_sel_req = MagicMock()
        mock_sel_req.type = "SelectionRequest"

        def wait_side_effect(*args, **kwargs):
            args[3].append(mock_sel_req)
            return mock_event

        chunks = [b"data", b""]
        wait_patch = patch("pclipsync.selection_utils.wait_for_property_notify", side_effect=wait_side_effect)
        read_patch = patch("pclipsync.clipboard_io._read_chunk_property", side_effect=chunks)
        with wait_patch, read_patch:
            result = _handle_incr_transfer(mock_display, mock_window, 123, deferred, 5.0)

        assert result == b"data"
        assert len(deferred) == 2
        assert all(e.type == "SelectionRequest" for e in deferred)
