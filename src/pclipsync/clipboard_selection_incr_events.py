"""INCR send event detection.

This module provides functions to detect events related to in-progress
INCR send transfers (PropertyNotify and DestroyNotify).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.protocol.rq import Event
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def is_incr_send_event(
    event: "Event", pending_incr_sends: dict[tuple[int, int], "IncrSendState"] | None
) -> tuple[bool, str | None]:
    """Check if an event is related to an in-progress INCR send transfer.

    Examines PropertyNotify (with PropertyDelete state) and DestroyNotify
    events to determine if they match a pending INCR send transfer.

    Args:
        event: The X11 event to check.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.

    Returns:
        Tuple of (is_match, event_type) where event_type is 'property_delete',
        'destroy', or None if not a matching event.
    """
    if not pending_incr_sends:
        return (False, None)
    if _is_property_delete_match(event, pending_incr_sends):
        return (True, "property_delete")
    if _is_destroy_match(event, pending_incr_sends):
        return (True, "destroy")
    return (False, None)


def _is_property_delete_match(
    event: "Event", pending_incr_sends: dict[tuple[int, int], "IncrSendState"]
) -> bool:
    """Check if event is PropertyNotify/PropertyDelete matching a transfer."""
    from Xlib import X
    if event.type != X.PropertyNotify or event.state != X.PropertyDelete:
        return False
    transfer_key = (event.window.id, event.atom)
    return transfer_key in pending_incr_sends


def _is_destroy_match(
    event: "Event", pending_incr_sends: dict[tuple[int, int], "IncrSendState"]
) -> bool:
    """Check if event is DestroyNotify matching a transfer's requestor."""
    from Xlib import X
    if event.type != X.DestroyNotify:
        return False
    requestor_ids = {key[0] for key in pending_incr_sends}
    return event.window.id in requestor_ids
