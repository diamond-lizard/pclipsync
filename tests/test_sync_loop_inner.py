#!/usr/bin/env python3
"""Tests for sync_loop_inner acquisition_time handling.

Tests that process_x11_events correctly stores and clears acquisition_time
based on SetSelectionOwnerNotify events.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def mock_clipboard_state() -> MagicMock:
    """Create a mock ClipboardState for testing."""
    state = MagicMock()
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.window.id = 12345
    state.current_content = b""
    state.acquisition_time = None
    return state


@pytest.fixture
def mock_writer() -> AsyncMock:
    """Create a mock StreamWriter for testing."""
    return AsyncMock()


def make_owner_event(owner_id: int, timestamp: int) -> MagicMock:
    """Create a mock SetSelectionOwnerNotify event."""
    event = MagicMock()
    # Make type(event).__name__ return "SetSelectionOwnerNotify"
    event.__class__.__name__ = "SetSelectionOwnerNotify"
    event.owner = MagicMock()
    event.owner.id = owner_id
    event.timestamp = timestamp
    event.selection = 1  # CLIPBOARD atom
    return event


@pytest.mark.asyncio
async def test_stores_timestamp_when_we_become_owner(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is set when we become selection owner."""
    # Create event where we become owner (event.owner.id == state.window.id)
    event = make_owner_event(owner_id=12345, timestamp=555666777)
    
    with patch(
        "pclipsync.sync_loop_inner.process_pending_events"
    ) as mock_pending, patch(
        "pclipsync.sync_loop_inner.handle_clipboard_change", new_callable=AsyncMock
    ) as mock_handler:
        mock_pending.return_value = [event]
        
        from pclipsync.sync_loop_inner import process_x11_events
        await process_x11_events(mock_clipboard_state, mock_writer)
    
    # acquisition_time should be set to event.timestamp
    assert mock_clipboard_state.acquisition_time == 555666777


@pytest.mark.asyncio
async def test_clears_timestamp_when_we_lose_ownership(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is cleared when we lose selection ownership."""
    # Set initial acquisition_time
    mock_clipboard_state.acquisition_time = 555666777
    
    # Create event where someone else becomes owner (event.owner.id != state.window.id)
    event = make_owner_event(owner_id=99999, timestamp=888999000)
    
    with patch(
        "pclipsync.sync_loop_inner.process_pending_events"
    ) as mock_pending, patch(
        "pclipsync.sync_loop_inner.handle_clipboard_change", new_callable=AsyncMock
    ) as mock_handler:
        mock_pending.return_value = [event]
        
        from pclipsync.sync_loop_inner import process_x11_events
        await process_x11_events(mock_clipboard_state, mock_writer)
    
    # acquisition_time should be cleared to None
    assert mock_clipboard_state.acquisition_time is None
