#!/usr/bin/env python3
"""
Tests for handle_clipboard_change function.

Tests duplicate/echo skipping and oversized content handling.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest



@pytest.mark.asyncio
async def test_handle_clipboard_change_skips_when_we_own_selection(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change returns early when we own the selection.

    This prevents infinite loops after mirroring to the other selection.
    When we set a selection, the XFixes event fires, but since we own it,
    we skip processing.
    """
    from pclipsync.sync_handlers import handle_clipboard_change

    # Mock get_selection_owner to return our window (we own the selection)
    mock_clipboard_state.display.get_selection_owner.return_value = (
        mock_clipboard_state.window
    )

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        # read_clipboard_content should NOT be called (early return)
        mock_read.assert_not_called()
        mock_writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clipboard_change_skips_empty(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change skips when clipboard is empty."""
    from pclipsync.sync_handlers import handle_clipboard_change

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        mock_read.return_value = None
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        mock_writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clipboard_change_skips_duplicate(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change skips duplicate content."""
    from pclipsync.hashing import compute_hash
    from pclipsync.sync_handlers import handle_clipboard_change

    content = b"duplicate content"
    mock_clipboard_state.hash_state.record_sent(compute_hash(content))

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        mock_read.return_value = content
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        mock_writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clipboard_change_skips_echo(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change skips echo content."""
    from pclipsync.hashing import compute_hash
    from pclipsync.sync_handlers import handle_clipboard_change

    content = b"echo content"
    mock_clipboard_state.hash_state.record_received(compute_hash(content))

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        mock_read.return_value = content
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        mock_writer.write.assert_not_called()
