#!/usr/bin/env python3
"""
Tests for handle_clipboard_change send and size limit behavior.

Tests oversized content rejection and successful new content sends.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest



@pytest.mark.asyncio
async def test_handle_clipboard_change_skips_oversized(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change skips oversized content with warning."""
    from pclipsync.sync_handlers import handle_clipboard_change

    # Create content larger than 10 MB
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        mock_read.return_value = oversized_content
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        mock_writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_handle_clipboard_change_sends_new_content(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test handle_clipboard_change sends new content."""
    from pclipsync.sync_handlers import handle_clipboard_change

    content = b"new clipboard content"

    with patch(
        "pclipsync.sync_handlers.read_clipboard_content", new_callable=AsyncMock
    ) as mock_read:
        mock_read.return_value = content
        await handle_clipboard_change(mock_clipboard_state, mock_writer, 1)
        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_called_once()
