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
from dataclasses import dataclass

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest
    from Xlib.protocol.rq import Event
    from Xlib.xobject.drawable import Window


# Safety margin for INCR threshold (90% of max)
INCR_SAFETY_MARGIN: float = 0.9

# Chunk size for INCR transfers (65536 bytes, well below typical max_request)
INCR_CHUNK_SIZE: int = 65536

# Maximum time to wait for INCR transfer completion (seconds)
INCR_SEND_TIMEOUT: float = 30.0

@dataclass
class IncrSendState:
    """State for an in-progress INCR send transfer.

    Tracks all information needed to send clipboard content in chunks
    via the INCR protocol when content exceeds the maximum property size.

    Attributes:
        requestor: The requestor window that requested the clipboard content.
        property_atom: The property atom where chunks should be written.
        target_atom: The target atom (e.g., UTF8_STRING) for the content type.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY).
        content: The full content bytes to send.
        offset: Current offset into content for the next chunk.
        start_time: Timestamp when the transfer started (for timeout).
        completion_sent: True if zero-length completion marker was sent.
    """

    requestor: Window
    property_atom: int
    target_atom: int
    selection_atom: int
    content: bytes
    offset: int
    start_time: float
    completion_sent: bool = False

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
    max_bytes = display.info.max_request_length * 4 # type: ignore[attr-defined]
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


def unsubscribe_requestor_events(display: "Display", requestor: "Window") -> None:
    """Clear event masks on a requestor window.

    Removes PropertyNotify and StructureNotify event subscriptions from
    a requestor window. If the window was destroyed, the X11 error will
    be printed to stderr but will not raise a Python exception.

    Args:
        display: The X11 display connection.
        requestor: The requestor window to unsubscribe from.
    """
    requestor.change_attributes(event_mask=0)
    display.flush()


def unsubscribe_incr_requestor(
    display: "Display",
    state: IncrSendState,
    transfer_key: tuple[int, int],
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
) -> None:
    """Unsubscribe from requestor events and remove transfer entry.

    Checks if other INCR transfers exist for the same requestor window.
    If this is the last transfer for the window, clears event masks.
    Always removes the transfer entry from pending_incr_sends.

    Args:
        display: The X11 display connection.
        state: The IncrSendState for this transfer.
        transfer_key: The (requestor_id, property_atom) tuple identifying this transfer.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    requestor_id = transfer_key[0]

    # Count transfers for this requestor window
    count = sum(1 for key in pending_incr_sends if key[0] == requestor_id)

    if count == 1:
        # This is the last transfer for the window - unsubscribe
        unsubscribe_requestor_events(display, state.requestor)

    # Remove the transfer entry
    if transfer_key in pending_incr_sends:
        del pending_incr_sends[transfer_key]

def initiate_incr_send(
    display: "Display",
    event: "SelectionRequest",
    content: bytes,
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
    incr_atom: int,
) -> None:
    """Initiate an INCR transfer for large clipboard content.

    Subscribes to PropertyNotify and StructureNotify events on the requestor
    window, writes INCR type with content length, creates transfer state,
    and sends SelectionNotify to begin the transfer.

    Args:
        display: The X11 display connection.
        event: The SelectionRequest event.
        content: The content bytes to send via INCR.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
        incr_atom: The INCR atom for type field.
    """
    from Xlib import X
    from Xlib.protocol.event import SelectionNotify as SelectionNotifyEvent
    import logging
    import time
    logger = logging.getLogger(__name__)

    # Subscribe to PropertyNotify and StructureNotify on requestor window
    event.requestor.change_attributes(
        event_mask=X.PropertyChangeMask | X.StructureNotifyMask
    )

    try:
        # Write INCR type with content length as value
        event.requestor.change_property(
            event.property, incr_atom, 32, [len(content)]
        )

        # Create transfer state entry
        transfer_key = (event.requestor.id, event.property)
        pending_incr_sends[transfer_key] = IncrSendState(
            requestor=event.requestor,
            property_atom=event.property,
            target_atom=event.target,
            selection_atom=event.selection,
            content=content,
            offset=0,
            start_time=time.time(),
        )

        # Send SelectionNotify to tell requestor property is ready
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
        logger.debug("Initiated INCR send: requestor=%s property=%s size=%s",
            event.requestor.id, event.property, len(content))

    except Exception:
        # Clean up subscription on error
        unsubscribe_requestor_events(display, event.requestor)
        # Refuse the request
        event.property = X.NONE
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
        raise


def send_incr_chunk(
    display: "Display",
    state: IncrSendState,
    transfer_key: tuple[int, int],
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
) -> None:
    """Send the next chunk of an INCR transfer.

    Calculates and sends the next chunk of content based on current offset.
    If all content has been sent, writes a zero-length chunk to signal
    completion. Updates the offset in state after sending.

    Args:
        display: The X11 display connection.
        state: The IncrSendState for this transfer.
        transfer_key: The (requestor_id, property_atom) tuple identifying this transfer.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import logging
    logger = logging.getLogger(__name__)

    content_length = len(state.content)

    if state.offset >= content_length:
        # All real data was sent - write zero-length completion marker
        state.requestor.change_property(
            state.property_atom, state.target_atom, 8, b""
        )
        display.flush()
        state.completion_sent = True
        logger.debug("INCR send complete: requestor=%s property=%s",
            transfer_key[0], transfer_key[1])
        return

    # Calculate next chunk
    from pclipsync.clipboard_selection import INCR_CHUNK_SIZE
    chunk_end = min(state.offset + INCR_CHUNK_SIZE, content_length)
    chunk = state.content[state.offset:chunk_end]

    # Write chunk to requestor's property
    state.requestor.change_property(
        state.property_atom, state.target_atom, 8, chunk
    )
    display.flush()

    # Update offset
    state.offset = chunk_end
    logger.debug("INCR chunk sent: requestor=%s property=%s offset=%s/%s",
        transfer_key[0], transfer_key[1], state.offset, content_length)
def handle_selection_request(
    display: Display,
    event: SelectionRequest,
    content: bytes,
    acquisition_time: int | None,
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
    incr_atom: int,
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
        # Return content - check if INCR transfer is needed
        if not needs_incr_transfer(content, display):
            # Small content - send directly
            event.requestor.change_property(
                event.property, event.target, 8, content
            )
        else:
            # Large content - use INCR protocol
            initiate_incr_send(
                display, event, content, pending_incr_sends, incr_atom
            )
            return  # INCR sends its own SelectionNotify
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


def is_incr_send_event(
    event: "Event", pending_incr_sends: dict[tuple[int, int], IncrSendState] | None
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
    from Xlib import X

    if not pending_incr_sends:
        return (False, None)

    # Check for PropertyNotify with PropertyDelete state
    if event.type == X.PropertyNotify and event.state == X.PropertyDelete:
        transfer_key = (event.window.id, event.atom)
        if transfer_key in pending_incr_sends:
            return (True, "property_delete")

    # Check for DestroyNotify matching any pending transfer's requestor
    if event.type == X.DestroyNotify:
        for (requestor_id, _) in pending_incr_sends:
            if event.window.id == requestor_id:
                return (True, "destroy")

    return (False, None)

def handle_incr_send_event(
    display: "Display",
    event: "Event",
    event_type: str,
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
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
    import logging
    logger = logging.getLogger(__name__)

    if event_type == "destroy":
        # Requestor window was destroyed - clean up all transfers for it
        logger.debug("INCR send: requestor window destroyed: %s", event.window.id)
        # Collect keys to remove (avoid modifying dict during iteration)
        keys_to_remove = [
            key for key in pending_incr_sends if key[0] == event.window.id
        ]
        for key in keys_to_remove:
            state = pending_incr_sends[key]
            unsubscribe_incr_requestor(display, state, key, pending_incr_sends)
        return

    # event_type == "property_delete"
    transfer_key = (event.window.id, event.atom)
    transfer_state = pending_incr_sends.get(transfer_key)
    if transfer_state is None:
        return

    if transfer_state.completion_sent:
        # Final acknowledgment - requestor deleted zero-length property
        logger.debug("INCR send: final ack received, cleaning up: %s", transfer_key)
        unsubscribe_incr_requestor(display, transfer_state, transfer_key, pending_incr_sends)
    else:
        # Requestor deleted property - send next chunk
        send_incr_chunk(display, transfer_state, transfer_key, pending_incr_sends)


def cleanup_stale_incr_sends(
    display: "Display",
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
) -> None:
    """Remove INCR send transfers that have exceeded the timeout.

    Iterates over a snapshot of pending_incr_sends to avoid RuntimeError
    from modifying dict during iteration. For each stale transfer, logs
    a warning and calls unsubscribe_incr_requestor to clean up.

    Args:
        display: The X11 display connection.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import time
    import logging
    logger = logging.getLogger(__name__)

    current_time = time.time()
    # Snapshot to avoid modifying dict during iteration
    for key, state in list(pending_incr_sends.items()):
        elapsed = current_time - state.start_time
        if elapsed > INCR_SEND_TIMEOUT:
            logger.warning(
                "INCR send: transfer timed out after %.1f seconds: %s",
                elapsed,
                key,
            )
            unsubscribe_incr_requestor(display, state, key, pending_incr_sends)


def cleanup_incr_sends_on_ownership_loss(
    display: "Display",
    selection_atom: int,
    pending_incr_sends: dict[tuple[int, int], IncrSendState],
) -> None:
    """Clean up INCR send transfers when losing selection ownership.

    When we lose ownership of a selection, any pending INCR transfers for
    that selection are no longer valid (the content we were serving may
    have changed). Collects matching entries into a list first to avoid
    modifying dict during iteration.

    Args:
        display: The X11 display connection.
        selection_atom: The selection atom we lost ownership of.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import logging
    logger = logging.getLogger(__name__)

    # Collect keys for this selection (avoid modifying dict during iteration)
    keys_to_remove = [
        key for key, state in pending_incr_sends.items()
        if state.selection_atom == selection_atom
    ]

    for key in keys_to_remove:
        state = pending_incr_sends[key]
        logger.debug("INCR send: ownership lost, canceling transfer: %s", key)
        unsubscribe_incr_requestor(display, state, key, pending_incr_sends)

def process_pending_events(
    display: Display, deferred_events: list["Event"] | None = None, pending_incr_sends: dict[tuple[int, int], IncrSendState] | None = None
) -> list[Event]:
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
    logger = logging.getLogger(__name__)

    # Clean up stale INCR transfers before processing events
    if pending_incr_sends is not None:
        cleanup_stale_incr_sends(display, pending_incr_sends)
    events: list[Event] = []
    # Drain deferred events first (preserves event ordering)
    if deferred_events:
        events.extend(deferred_events)
        deferred_events.clear()
    while display.pending_events() > 0:
        event = display.next_event()
        logger.debug("X11 event type=%s class=%s", event.type, type(event).__name__)
        # Check for INCR send events first
        is_match, evt_type = is_incr_send_event(event, pending_incr_sends)
        if is_match and pending_incr_sends is not None and evt_type is not None:
            handle_incr_send_event(display, event, evt_type, pending_incr_sends)
            continue
        # Collect SelectionRequest and XFixes events
        if event.type == X.SelectionRequest:
            events.append(event)
        elif type(event).__name__ == "SetSelectionOwnerNotify":
            # XFixes SetSelectionOwnerNotify event
            events.append(event)
    return events
