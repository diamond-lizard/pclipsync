#!/usr/bin/env python3
"""Tests for clipboard selection event processing."""
from unittest.mock import MagicMock


def test_process_pending_events_drains_deferred_first() -> None:
    """Deferred events are drained and prepended before pending events."""
    from pclipsync.clipboard_selection import process_pending_events

    mock_display = MagicMock()
    mock_display.pending_events.return_value = 0  # No new pending events

    # Create mock deferred events
    deferred1 = MagicMock()
    deferred2 = MagicMock()
    deferred_events = [deferred1, deferred2]

    result = process_pending_events(mock_display, deferred_events)

    assert result == [deferred1, deferred2]


def test_process_pending_events_clears_deferred_list() -> None:
    """Deferred events list is cleared after draining."""
    from pclipsync.clipboard_selection import process_pending_events

    mock_display = MagicMock()
    mock_display.pending_events.return_value = 0

    deferred_events = [MagicMock(), MagicMock()]

    process_pending_events(mock_display, deferred_events)

    assert deferred_events == []
