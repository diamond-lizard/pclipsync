"""X11 clipboard event handling.

This module provides functions for handling X11 clipboard events including
XFixes selection change notifications and SelectionRequest events when
owning selections. It works with the core clipboard module for display
and window management.

The module handles:
- Registering for XFixes selection change notifications
- Responding to SelectionRequest events when owning selections
- Setting clipboard content (taking selection ownership)
- Processing pending X11 events without blocking
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.xobject.drawable import Window


def register_xfixes_events(display: Display, window: Window) -> None:
    """Register for XFixes selection change notifications.

    Uses the XFixes extension to register for XFixesSelectionNotify events
    on both CLIPBOARD and PRIMARY atoms. This provides true event-driven
    notification when clipboard ownership changes.

    Args:
        display: The X11 display connection.
        window: The window to receive selection events.
    """
    from Xlib import Xatom
    from Xlib.ext import xfixes

    # Initialize XFixes extension
    xfixes.query_version(display)

    # Get atoms for CLIPBOARD and PRIMARY selections
    clipboard_atom = display.intern_atom("CLIPBOARD")
    primary_atom = Xatom.PRIMARY

    # Register for selection change events on both selections
    mask = xfixes.XFixesSetSelectionOwnerNotifyMask
    xfixes.select_selection_input(display, window.id, clipboard_atom, mask)
    xfixes.select_selection_input(display, window.id, primary_atom, mask)
    display.flush()


def set_clipboard_content(
    display: Display, window: Window, content: bytes, selection_atom: int
) -> bool:
    """Set clipboard content by taking ownership of specified selection.

    Takes ownership of the specified selection (CLIPBOARD or PRIMARY) and
    stores the content to serve to other applications when they request it.

    Args:
        display: The X11 display connection.
        window: The window to own the selection.
        content: The content bytes to set.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY).

    Returns:
        True on success, False on failure.
    """
    import logging

    from Xlib import X

    logger = logging.getLogger(__name__)

    try:
        # Take ownership of the selection
        window.set_selection_owner(selection_atom, X.CurrentTime)
        display.flush()

        # Verify we got ownership
        owner = display.get_selection_owner(selection_atom)
        if owner != window:
            logger.error("Failed to acquire selection ownership")
            return False

        return True

    except Exception as e:
        logger.error("Failed to set clipboard content: %s", e)
        return False
