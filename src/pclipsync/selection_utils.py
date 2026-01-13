#!/usr/bin/env python3
"""X11 selection utility functions.

This module provides helper functions for working with X11 selections,
including resolving selection atoms and shared event-waiting utilities.
"""

from __future__ import annotations

from Xlib import Xatom
from time import monotonic as _monotonic

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.rq import Event
    from Xlib.xobject.drawable import Window

# Timeout for waiting for our own property change (should always succeed quickly)
TIMESTAMP_TIMEOUT: float = 1.0


def get_other_selection(selection_atom: int, clipboard_atom: int) -> int:
    """Return the other selection atom.
    
    Given a selection atom, returns the other selection. If selection_atom
    is CLIPBOARD, returns PRIMARY. If selection_atom is PRIMARY (or any
    other value), returns CLIPBOARD.
    
    Args:
        selection_atom: The selection atom that changed.
        clipboard_atom: The cached CLIPBOARD atom.
    
    Returns:
        The atom of the other selection.
    """
    if selection_atom == clipboard_atom:
        return Xatom.PRIMARY
    return clipboard_atom


def wait_for_event_type(
    display: "Display",
    target_event_type: int,
    deferred_events: list["Event"],
    timeout: float,
) -> "Event | None":
    """Poll display for an event of the target type with timeout.

    Reads events from the display until an event of target_event_type
    is found or timeout expires. Uses select() on the display file
    descriptor to avoid blocking indefinitely. Other events
    (SelectionRequest, SetSelectionOwnerNotify) are appended to
    deferred_events for later processing.

    Args:
        display: The X11 display connection.
        target_event_type: The X11 event type to wait for.
        deferred_events: List to collect other events during wait.
        timeout: Maximum seconds to wait for the event.

    Returns:
        The matching event of target_event_type, or None if timeout.
    """
    import select
    from Xlib import X

    deadline = _monotonic() + timeout
    while True:
        # Check for already-buffered events first
        while display.pending_events() > 0:
            event = display.next_event()
            if event.type == target_event_type:
                return event
            # Defer SelectionRequest and SetSelectionOwnerNotify
            if event.type == X.SelectionRequest:
                deferred_events.append(event)
            elif type(event).__name__ == "SetSelectionOwnerNotify":
                deferred_events.append(event)

        # Calculate remaining time
        remaining = deadline - _monotonic()
        if remaining <= 0:
            return None

        # Wait for data with timeout
        readable, _, _ = select.select([display.fileno()], [], [], remaining)
        if not readable:
            return None


def get_server_timestamp(
    display: "Display",
    window: "Window",
    deferred_events: list["Event"],
) -> int | None:
    """Query the X server's current timestamp.

    Uses the PropertyNotify pattern: change a dummy property on the
    window, flush, and wait for the PropertyNotify event whose timestamp
    reflects the server's current time. This adds one round-trip (~0.1ms).

    Args:
        display: The X11 display connection.
        window: The window to change a property on.
        deferred_events: List to collect other events during wait.

    Returns:
        The X server's current timestamp, or None if timeout (unexpected).
    """
    from Xlib import X, Xatom

    # Change a dummy property to trigger PropertyNotify
    prop_atom = display.intern_atom("PCLIPSYNC_TIMESTAMP")
    window.change_property(prop_atom, Xatom.INTEGER, 32, [0])
    display.flush()

    # Wait for PropertyNotify with timeout
    event = wait_for_event_type(
        display, X.PropertyNotify, deferred_events, TIMESTAMP_TIMEOUT
    )
    if event is None:
        return None
    return event.time


def wait_for_property_notify(
    display: "Display",
    window: "Window",
    prop_atom: int,
    deferred_events: list["Event"],
    timeout: float,
) -> "Event | None":
    """Wait for PropertyNotify event with matching criteria.

    Waits for a PropertyNotify event matching the specified window,
    property atom, and state=PropertyNewValue. Uses select-based
    timeout to avoid blocking indefinitely. Defers SelectionRequest
    and SetSelectionOwnerNotify events for later processing.

    Args:
        display: The X11 display connection.
        window: The window to match in the event.
        prop_atom: The property atom to match in the event.
        deferred_events: List to collect other events during wait.
        timeout: Maximum seconds to wait for the event.

    Returns:
        The matching PropertyNotify event, or None if timeout.
    """
    import select
    from Xlib import X

    deadline = _monotonic() + timeout
    while True:
        # Check for already-buffered events first
        while display.pending_events() > 0:
            event = display.next_event()
            # Check for matching PropertyNotify
            if (event.type == X.PropertyNotify and
                    event.window == window and
                    event.atom == prop_atom and
                    event.state == X.PropertyNewValue):
                return event
            # Defer SelectionRequest and SetSelectionOwnerNotify
            if event.type == X.SelectionRequest:
                deferred_events.append(event)
            elif type(event).__name__ == "SetSelectionOwnerNotify":
                deferred_events.append(event)

        # Calculate remaining time
        remaining = deadline - _monotonic()
        if remaining <= 0:
            return None

        # Wait for data with timeout
        readable, _, _ = select.select([display.fileno()], [], [], remaining)
        if not readable:
            return None
