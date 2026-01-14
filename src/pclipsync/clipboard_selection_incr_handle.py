"""INCR send event handlers.

This module provides functions to handle PropertyNotify and DestroyNotify
events for in-progress INCR send transfers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.rq import Event
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def handle_incr_send_event(
    display: "Display", event: "Event", event_type: str,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Handle an INCR send-related event.

    Processes PropertyNotify (property_delete) and DestroyNotify events
    for in-progress INCR send transfers.

    Args:
        display: The X11 display connection.
        event: The X11 event.
        event_type: Either 'property_delete' or 'destroy'.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    if event_type == "destroy":
        _handle_destroy_event(display, event, pending_incr_sends)
    else:
        _handle_property_delete(display, event, pending_incr_sends)


def _handle_destroy_event(
    display: "Display", event: "Event",
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Handle DestroyNotify for an INCR transfer requestor."""
    import logging
    from pclipsync.clipboard_selection_incr_subscribe import unsubscribe_incr_requestor
    logger = logging.getLogger(__name__)
    logger.debug("INCR send: requestor window destroyed: %s", event.window.id)
    keys_to_remove = [key for key in pending_incr_sends if key[0] == event.window.id]
    for key in keys_to_remove:
        unsubscribe_incr_requestor(display, pending_incr_sends[key], key, pending_incr_sends)


def _handle_property_delete(
    display: "Display", event: "Event",
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Handle PropertyNotify with PropertyDelete for an INCR transfer."""
    import logging
    from pclipsync.clipboard_selection_incr_chunk import send_incr_chunk
    from pclipsync.clipboard_selection_incr_subscribe import unsubscribe_incr_requestor
    logger = logging.getLogger(__name__)
    transfer_key = (event.window.id, event.atom)
    state = pending_incr_sends.get(transfer_key)
    if state is None:
        return
    if state.completion_sent:
        logger.debug("INCR send: final ack received, cleaning up: %s", transfer_key)
        unsubscribe_incr_requestor(display, state, transfer_key, pending_incr_sends)
    else:
        send_incr_chunk(display, state, transfer_key, pending_incr_sends)
