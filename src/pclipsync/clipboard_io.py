"""X11 clipboard I/O operations.

This module provides functions for reading and writing X11 clipboard content,
handling SelectionRequest events, and processing pending X11 events. It works
with the core clipboard module for display and window management.

The module handles:
- Reading clipboard content with timeout handling
- Setting clipboard content (taking selection ownership)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.xobject.drawable import Window

# Timeout in seconds for clipboard read operations to prevent hangs
# when the clipboard owner is unresponsive
CLIPBOARD_TIMEOUT: float = 2.0


async def read_clipboard_content(
    display: Display, window: Window, selection_atom: int
) -> bytes | None:
    """Read clipboard content from the current selection owner.

    Requests UTF8_STRING target from the current clipboard owner and returns
    the content bytes. Uses asyncio.wait_for with CLIPBOARD_TIMEOUT to prevent
    hangs when the clipboard owner is unresponsive.

    Args:
        display: The X11 display connection.
        window: The window to receive selection data.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY).

    Returns:
        Content bytes if successful, None on failure/empty/timeout.
    """
    import asyncio
    import logging

    from Xlib import X

    logger = logging.getLogger(__name__)

    try:

        # Get selection owner
        owner = display.get_selection_owner(selection_atom)
        if owner == X.NONE:
            logger.debug("No selection owner for atom %s", selection_atom)
            return None

        # Request clipboard content via X11 selection protocol
        utf8_atom = display.intern_atom("UTF8_STRING")
        prop_atom = display.intern_atom("PCLIPSYNC_SEL")
        
        # Request selection conversion
        window.convert_selection(selection_atom, utf8_atom, prop_atom, X.CurrentTime)
        display.flush()
        
        # Poll for SelectionNotify with timeout
        content = await _wait_for_selection(display, window, prop_atom)
        return content

    except asyncio.TimeoutError:
        logger.debug("Clipboard read timed out after %s seconds", CLIPBOARD_TIMEOUT)
        return None
    except Exception as e:
        logger.debug("Clipboard read failed: %s", e)
        return None


async def _wait_for_selection(
    display: "Display", window: "Window", prop_atom: int
) -> bytes | None:
    """Wait for SelectionNotify and read property data.
    
    Polls for SelectionNotify event with timeout, then reads
    the property data from the window.
    
    Args:
        display: The X11 display connection.
        window: The window that requested the selection.
        prop_atom: The property atom where data will be stored.
    
    Returns:
        Content bytes if successful, None on failure/timeout.
    """
    import asyncio
    import logging
    
    from Xlib import X
    
    logger = logging.getLogger(__name__)
    poll_interval = 0.01
    elapsed = 0.0
    
    while elapsed < CLIPBOARD_TIMEOUT:
        while display.pending_events() > 0:
            event = display.next_event()
            if event.type == X.SelectionNotify:
                return _read_selection_property(display, window, prop_atom)
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    
    logger.debug("Timeout waiting for SelectionNotify")
    return None


def _read_selection_property(
    display: "Display", window: "Window", prop_atom: int
) -> bytes | None:
    """Read and delete selection property from window.
    
    Args:
        display: The X11 display connection.
        window: The window containing the property.
        prop_atom: The property atom to read.
    
    Returns:
        Content bytes if successful, None on failure.
    """
    import logging
    
    from Xlib import X
    
    logger = logging.getLogger(__name__)
    
    try:
        prop = window.get_full_property(prop_atom, X.AnyPropertyType)
        window.delete_property(prop_atom)
        display.flush()
        
        if prop is None:
            logger.debug("Selection property was empty")
            return None
        
        data = prop.value
        if isinstance(data, str):
            return data.encode("utf-8")
        return bytes(data)
    except Exception as e:
        logger.debug("Failed to read selection property: %s", e)
        return None
