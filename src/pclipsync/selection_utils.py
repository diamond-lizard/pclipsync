#!/usr/bin/env python3
"""X11 selection utility functions.

This module provides helper functions for working with X11 selections,
including resolving selection atoms and shared event-waiting utilities.
"""

from __future__ import annotations

from Xlib import Xatom

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.rq import Event
    from Xlib.xobject.drawable import Window


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
) -> "Event":
    """Poll display for an event of the target type.
    
    Reads events from the display until an event of target_event_type
    is found. Other events (SelectionRequest, SetSelectionOwnerNotify)
    are appended to deferred_events for later processing.
    
    This is a blocking operation that should only be called when
    events are expected (after convert_selection or property change).
    
    Args:
        display: The X11 display connection.
        target_event_type: The X11 event type to wait for.
        deferred_events: List to collect other events during wait.
    
    Returns:
        The matching event of target_event_type.
    """
    from Xlib import X
    
    while True:
        event = display.next_event()
        if event.type == target_event_type:
            return event
        # Defer SelectionRequest and SetSelectionOwnerNotify
        if event.type == X.SelectionRequest:
            deferred_events.append(event)
        elif type(event).__name__ == "SetSelectionOwnerNotify":
            deferred_events.append(event)


def get_server_timestamp(
    display: "Display",
    window: "Window",
    deferred_events: list["Event"],
) -> int:
    """Query the X server's current timestamp.
    
    Uses the PropertyNotify pattern: change a dummy property on the
    window, flush, and wait for the PropertyNotify event whose timestamp
    reflects the server's current time. This adds one round-trip (~0.1ms).
    
    Args:
        display: The X11 display connection.
        window: The window to change a property on.
        deferred_events: List to collect other events during wait.
    
    Returns:
        The X server's current timestamp.
    """
    from Xlib import X, Xatom
    
    # Change a dummy property to trigger PropertyNotify
    prop_atom = display.intern_atom("PCLIPSYNC_TIMESTAMP")
    window.change_property(prop_atom, Xatom.INTEGER, 32, [0])
    display.flush()
    
    # Wait for PropertyNotify
    event = wait_for_event_type(display, X.PropertyNotify, deferred_events)
    return event.time
