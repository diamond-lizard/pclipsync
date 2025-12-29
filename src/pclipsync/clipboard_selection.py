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


def handle_selection_request(
    display: Display, event: object, content: bytes
) -> None:
    """Respond to SelectionRequest events when owning selections.

    Handles requests from other applications for clipboard content. Supports
    TARGETS (list of available targets), UTF8_STRING (preferred), and STRING
    (legacy). Refuses unsupported targets with SelectionNotify property=None.

    Args:
        display: The X11 display connection.
        event: The SelectionRequest event.
        content: The content bytes to serve.
    """
    from Xlib import X, Xatom

    # Get required atoms
    targets_atom = display.intern_atom("TARGETS")
    utf8_atom = display.intern_atom("UTF8_STRING")

    # Determine target and set property
    if event.target == targets_atom:
        # Return list of supported targets
        targets = [targets_atom, utf8_atom, Xatom.STRING]
        event.requestor.change_property(
            event.property, Xatom.ATOM, 32, targets
        )
    elif event.target in (utf8_atom, Xatom.STRING):
        # Return content
        event.requestor.change_property(
            event.property, event.target, 8, content
        )
    else:
        # Refuse unsupported target
        event.property = X.NONE

    # Send SelectionNotify response
    event.requestor.send_event(
        display.intern_atom("SelectionNotify", only_if_exists=True),
        event_mask=0,
        event=display.create_event(
            X.SelectionNotify,
            requestor=event.requestor,
            selection=event.selection,
            target=event.target,
            property=event.property,
            time=event.time,
        ),
    )
    display.flush()


def process_pending_events(display: Display) -> list[object]:
    """Process only events already pending without blocking.

    Checks pending_events() before processing to avoid stalling the asyncio
    event loop. Returns a list of relevant events (XFixesSelectionNotify
    and SelectionRequest) for processing.

    Args:
        display: The X11 display connection.

    Returns:
        List of pending events for processing.
    """
    from Xlib import X

    events = []
    while display.pending_events() > 0:
        event = display.next_event()
        # Collect SelectionRequest and XFixes events
        if event.type == X.SelectionRequest:
            events.append(event)
        elif hasattr(event, "subcode"):
            # XFixes events have a subcode attribute
            events.append(event)
    return events
