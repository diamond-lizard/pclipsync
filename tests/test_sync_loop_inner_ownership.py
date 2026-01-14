#!/usr/bin/env python3
"""Tests for sync_loop_inner acquisition_time handling.

Tests that process_x11_events correctly clears acquisition_time
when ownership is lost via SetSelectionOwnerNotify events.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest_sync_loop_inner import make_owner_event

@pytest.mark.asyncio
async def test_clears_timestamp_when_we_lose_ownership(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is cleared when we lose selection ownership."""
    # Set initial acquisition_time
    mock_clipboard_state.acquisition_time = 555666777
    mock_clipboard_state.owned_selections = {1}  # We own CLIPBOARD (selection=1)

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
    assert mock_clipboard_state.owned_selections == set()


@pytest.mark.asyncio
async def test_partial_ownership_loss_keeps_acquisition_time(
    mock_clipboard_state: MagicMock, mock_writer: AsyncMock
) -> None:
    """Test acquisition_time is NOT cleared when we still own another selection."""
    # Set initial state: we own both CLIPBOARD (1) and PRIMARY (Xatom.PRIMARY)
    mock_clipboard_state.acquisition_time = 555666777
    mock_clipboard_state.owned_selections = {1, 2}  # CLIPBOARD and PRIMARY

    # Create event where someone else takes CLIPBOARD (selection=1)
    event = make_owner_event(owner_id=99999, timestamp=888999000)

    with patch(
        "pclipsync.sync_loop_inner.process_pending_events"
    ) as mock_pending, patch(
        "pclipsync.sync_loop_inner.handle_clipboard_change", new_callable=AsyncMock
    ) as mock_handler:
        mock_pending.return_value = [event]

        from pclipsync.sync_loop_inner import process_x11_events
        await process_x11_events(mock_clipboard_state, mock_writer)

    # CLIPBOARD should be removed from owned_selections
    assert 1 not in mock_clipboard_state.owned_selections
    # But PRIMARY is still owned
    assert 2 in mock_clipboard_state.owned_selections
    # acquisition_time should NOT be cleared (we still own PRIMARY)
    assert mock_clipboard_state.acquisition_time == 555666777
