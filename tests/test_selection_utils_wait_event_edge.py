#!/usr/bin/env python3
"""Edge case tests for wait_for_event_type function.

Tests for ignored events and timeout behavior.
"""

from unittest.mock import MagicMock, patch

from Xlib import X

from pclipsync.selection_utils import wait_for_event_type


class TestWaitForEventTypeEdgeCases:
    """Edge case tests for wait_for_event_type function."""

    def test_ignores_other_events(self) -> None:
        """Discard events that are not target or deferrable types."""
        mock_display = MagicMock()

        other_event = MagicMock()
        other_event.type = X.Expose  # Not deferrable
        type(other_event).__name__ = "Expose"

        target_event = MagicMock()
        target_event.type = X.SelectionNotify

        mock_display.next_event.side_effect = [other_event, target_event]
        mock_display.pending_events.side_effect = [1, 1, 0]

        deferred: list = []
        result = wait_for_event_type(
            mock_display, X.SelectionNotify, deferred, timeout=1.0
        )

        assert result == target_event
        assert deferred == []  # other_event was discarded, not deferred

    def test_returns_none_on_timeout(self) -> None:
        """Return None when select times out waiting for events."""
        mock_display = MagicMock()
        mock_display.pending_events.return_value = 0
        mock_display.fileno.return_value = 3

        deferred: list = []
        with patch("select.select", return_value=([], [], [])):
            result = wait_for_event_type(
                mock_display, X.SelectionNotify, deferred, timeout=0.1
            )

        assert result is None
        assert deferred == []
