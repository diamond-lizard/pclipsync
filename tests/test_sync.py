#!/usr/bin/env python3
"""
Tests for clipboard synchronization handlers.

Tests handle_clipboard_change for duplicate/echo skipping and oversized
content handling, and handle_incoming_content for proper hash ordering.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import asyncio
import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def mock_clipboard_state() -> MagicMock:
    """Create a mock ClipboardState for testing."""
    state = MagicMock()
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.current_content = b""
    state.deferred_events = []
    state.x11_event = asyncio.Event()
    state.owned_selections = set()
    state.clipboard_atom = MagicMock()
    return state


@pytest.fixture
def mock_writer() -> AsyncMock:
    """Create a mock StreamWriter for testing."""
    writer = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    return writer


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


@pytest.mark.asyncio
async def test_handle_incoming_content_sets_hash_before_clipboard(
    mock_clipboard_state: MagicMock,
) -> None:
    """Test handle_incoming_content sets hash before setting clipboard."""
    from pclipsync.hashing import compute_hash
    from pclipsync.sync_handlers import handle_incoming_content

    content = b"incoming content"
    expected_hash = compute_hash(content)

    # Track call order
    call_order: list[str] = []

    def track_record_received(h: str) -> None:
        call_order.append("record_received")

    mock_clipboard_state.hash_state.record_received = track_record_received

    with patch("pclipsync.sync_handlers.set_clipboard_content") as mock_set, \
        patch("pclipsync.sync_handlers.get_server_timestamp", return_value=12345):
        def track_set(*args: object, **kwargs: object) -> bool:
            call_order.append("set_clipboard")
            return True

        mock_set.side_effect = track_set
        await handle_incoming_content(mock_clipboard_state, content)

    # Verify record_received was called before set_clipboard
    assert call_order[0] == "record_received"
    assert "set_clipboard" in call_order
