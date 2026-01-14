"""X11 event processing for clipboard synchronization.

This module provides the function to process pending X11 events without
blocking the asyncio event loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.rq import Event
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def process_pending_events(
    display: "Display",
    deferred_events: list["Event"] | None = None,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"] | None = None,
) -> list["Event"]:
    """Process only events already pending without blocking.

    Checks pending_events() before processing to avoid stalling the asyncio
    event loop. Returns a list of relevant events (XFixesSelectionNotify
    and SelectionRequest) for processing.

    Args:
        display: The X11 display connection.
        deferred_events: Optional list of events deferred during clipboard
            reads. These will be drained and prepended to the result.
        pending_incr_sends: Optional dict tracking in-progress INCR send
            transfers. Used for routing PropertyNotify events.

    Returns:
        List of pending events for processing.
    """
    from Xlib import X
    import logging
    from pclipsync.clipboard_selection_incr_cleanup import cleanup_stale_incr_sends
    from pclipsync.clipboard_selection_incr_events import is_incr_send_event
    from pclipsync.clipboard_selection_incr_handle import handle_incr_send_event
    logger = logging.getLogger(__name__)

    if pending_incr_sends is not None:
        cleanup_stale_incr_sends(display, pending_incr_sends)

    events: list[Event] = []
    if deferred_events:
        events.extend(deferred_events)
        deferred_events.clear()

    while display.pending_events() > 0:
        event = display.next_event()
        logger.debug("X11 event type=%s class=%s", event.type, type(event).__name__)
        is_match, evt_type = is_incr_send_event(event, pending_incr_sends)
        if is_match and pending_incr_sends is not None and evt_type is not None:
            handle_incr_send_event(display, event, evt_type, pending_incr_sends)
            continue
        if event.type == X.SelectionRequest:
            events.append(event)
        elif type(event).__name__ == "SetSelectionOwnerNotify":
            events.append(event)

    return events
