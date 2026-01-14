#!/usr/bin/env python3
"""
Tests for handle_incoming_content function.

Tests proper hash ordering when receiving clipboard content.
"""
from unittest.mock import MagicMock, patch

import pytest



def make_call_tracker(call_order: list[str], label: str) -> callable:
    """Create a callback that records when it was called.

    Args:
        call_order: List to append call labels to.
        label: Label to append when this callback is invoked.

    Returns:
        A callable that appends label to call_order and returns True.
    """
    def tracker(*args: object, **kwargs: object) -> bool:
        call_order.append(label)
        return True
    return tracker


@pytest.mark.asyncio
async def test_handle_incoming_content_sets_hash_before_clipboard(
    mock_clipboard_state: MagicMock,
) -> None:
    """Test handle_incoming_content sets hash before setting clipboard."""
    from pclipsync.sync_handlers import handle_incoming_content

    content = b"incoming content"
    call_order: list[str] = []

    mock_clipboard_state.hash_state.record_received = make_call_tracker(
        call_order, "record_received"
    )

    with patch("pclipsync.sync_handlers.set_clipboard_content") as mock_set, \
        patch("pclipsync.sync_handlers.get_server_timestamp", return_value=12345):
        mock_set.side_effect = make_call_tracker(call_order, "set_clipboard")
        await handle_incoming_content(mock_clipboard_state, content)

    # Verify record_received was called before set_clipboard
    assert call_order[0] == "record_received"
    assert "set_clipboard" in call_order
