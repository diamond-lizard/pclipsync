#!/usr/bin/env python3
"""Tests for INCR transfer detection."""
from unittest.mock import MagicMock


def test_needs_incr_transfer_false_for_small_content() -> None:
    """Test needs_incr_transfer returns False for content under threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer

    mock_display = MagicMock()
    # Set max_request_length to 65536 (256KB max property size)
    mock_display.info.max_request_length = 65536

    # Small content should not need INCR
    small_content = b"Hello, World!"
    assert needs_incr_transfer(small_content, mock_display) is False


def test_needs_incr_transfer_true_for_large_content() -> None:
    """Test needs_incr_transfer returns True for content exceeding threshold."""
    from pclipsync.clipboard_selection import needs_incr_transfer, INCR_SAFETY_MARGIN

    mock_display = MagicMock()
    # Set max_request_length to 1000 (4000 bytes max, ~3600 with safety margin)
    mock_display.info.max_request_length = 1000

    # Calculate threshold (1000 * 4 * 0.9 = 3600)
    threshold = int(1000 * 4 * INCR_SAFETY_MARGIN)

    # Content exceeding threshold should need INCR
    large_content = b"x" * (threshold + 1)
    assert needs_incr_transfer(large_content, mock_display) is True
