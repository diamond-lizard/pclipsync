#!/usr/bin/env python3
"""Helper functions for sync_loop_inner tests."""
from unittest.mock import MagicMock


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
