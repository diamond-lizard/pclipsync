"""X11 selection request handling.

This module provides functions for handling SelectionRequest events and
processing pending X11 events. When owning clipboard selections, the
application must respond to requests from other applications.

The module handles:
- Responding to SelectionRequest events (TARGETS, UTF8_STRING, STRING)
- Processing pending X11 events without blocking asyncio
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest
    from Xlib.protocol.rq import Event


# Safety margin for INCR threshold (90% of max)
INCR_SAFETY_MARGIN: float = 0.9

# Chunk size for INCR transfers (65536 bytes, well below typical max_request)
INCR_CHUNK_SIZE: int = 65536

# Maximum time to wait for INCR transfer completion (seconds)
INCR_SEND_TIMEOUT: float = 30.0

def get_max_property_size(display: "Display") -> int:
    """Return the maximum property size in bytes for a single change_property.

    The X11 protocol limits property writes based on max_request_length.
    This function calculates the threshold above which INCR must be used.
    A safety margin is applied to avoid edge cases.

    Args:
        display: The X11 display connection.

    Returns:
        Maximum safe property size in bytes.
    """
    # max_request_length is in 4-byte units; multiply by 4 for bytes
    # Apply safety margin to avoid edge cases near the limit
    max_bytes = display.info.max_request_length * 4
    return int(max_bytes * INCR_SAFETY_MARGIN)


def needs_incr_transfer(content: bytes, display: "Display") -> bool:
    """Check if content is too large for a single change_property.

    Returns True if the content length exceeds the maximum property size
    threshold, meaning INCR protocol must be used for the transfer.

    Args:
        content: The content bytes to check.
        display: The X11 display connection.

    Returns:
        True if INCR transfer is needed, False otherwise.
    """
    return len(content) > get_max_property_size(display)

def handle_selection_request(
    display: Display, event: SelectionRequest, content: bytes, acquisition_time: int | None
) -> None:
    """Respond to SelectionRequest events when owning selections.

    Handles requests from other applications for clipboard content. Supports
    TARGETS (list of available targets), UTF8_STRING (preferred), and STRING
    (legacy). Refuses unsupported targets with SelectionNotify property=None.

    Args:
        display: The X11 display connection.
        event: The SelectionRequest event.
        content: The content bytes to serve.
        acquisition_time: The X server timestamp when we acquired clipboard
            ownership, or None if unknown. Used for TIMESTAMP responses.
    """
    from Xlib import X, Xatom
    from Xlib.protocol.event import SelectionNotify as SelectionNotifyEvent
    import logging
    logger = logging.getLogger(__name__)

    # Get required atoms
    targets_atom = display.intern_atom("TARGETS")
    utf8_atom = display.intern_atom("UTF8_STRING")
    timestamp_atom = display.intern_atom("TIMESTAMP")
    logger.debug("SelectionRequest target=%s targets_atom=%s utf8=%s STRING=%s timestamp=%s prop=%s content_len=%s",
        event.target, targets_atom, utf8_atom, Xatom.STRING, timestamp_atom, event.property, len(content))

    # Determine target and set property
    if event.target == targets_atom:
        # Return list of supported targets
        targets = [targets_atom, utf8_atom, Xatom.STRING, timestamp_atom]
        event.requestor.change_property(
            event.property, Xatom.ATOM, 32, targets
        )
    elif event.target in (utf8_atom, Xatom.STRING):
        # Return content
        event.requestor.change_property(
            event.property, event.target, 8, content
        )
    elif event.target == timestamp_atom:
        # Return acquisition timestamp as 32-bit integer
        if acquisition_time is not None:
            event.requestor.change_property(
                event.property, Xatom.INTEGER, 32, [acquisition_time]
            )
            logger.debug("Handled TIMESTAMP request, returning time=%s", acquisition_time)
        else:
            # Refuse if we don't have a valid acquisition timestamp
            event.property = X.NONE
            logger.debug("Refused TIMESTAMP request, no acquisition_time")
    else:
        # Refuse unsupported target
        event.property = X.NONE

    # Send SelectionNotify response
    event.requestor.send_event(
        SelectionNotifyEvent(
            time=event.time,
            requestor=event.requestor.id,
            selection=event.selection,
            target=event.target,
            property=event.property,
        ),
        event_mask=0,
    )
    display.flush()


def process_pending_events(
    display: Display, deferred_events: list["Event"] | None = None
) -> list[Event]:
    """Process only events already pending without blocking.

    Checks pending_events() before processing to avoid stalling the asyncio
    event loop. Returns a list of relevant events (XFixesSelectionNotify
    and SelectionRequest) for processing.

    Args:
        display: The X11 display connection.
        deferred_events: Optional list of events deferred during clipboard
            reads. These will be drained and prepended to the result.

    Returns:
        List of pending events for processing.
    """
    from Xlib import X
    import logging
    logger = logging.getLogger(__name__)

    events: list[Event] = []
    # Drain deferred events first (preserves event ordering)
    if deferred_events:
        events.extend(deferred_events)
        deferred_events.clear()
    while display.pending_events() > 0:
        event = display.next_event()
        logger.debug("X11 event type=%s class=%s", event.type, type(event).__name__)
        # Collect SelectionRequest and XFixes events
        if event.type == X.SelectionRequest:
            events.append(event)
        elif type(event).__name__ == "SetSelectionOwnerNotify":
            # XFixes SetSelectionOwnerNotify event
            events.append(event)
    return events
