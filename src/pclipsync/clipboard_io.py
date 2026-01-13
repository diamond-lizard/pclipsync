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
    from Xlib.protocol.rq import Event
    import asyncio


from dataclasses import dataclass


@dataclass
class PropertyReadResult:
    """Result of reading an X11 selection property.

    Encapsulates the result of a property read, distinguishing between:
    - Normal content (is_incr=False, content contains the bytes)
    - INCR transfer initiation (is_incr=True, estimated_size set)
    - Failed read (content=None, is_incr=False)

    Attributes:
        content: The content bytes, or None if unavailable.
        is_incr: True if the property indicated INCR transfer.
        estimated_size: Estimated total size for INCR transfers.
    """

    content: bytes | None
    is_incr: bool
    estimated_size: int = 0


# Timeout in seconds for clipboard read operations to prevent hangs
# when the clipboard owner is unresponsive
CLIPBOARD_TIMEOUT: float = 2.0

# Timeout in seconds for each INCR chunk during incremental transfers
INCR_CHUNK_TIMEOUT: float = 5.0


async def read_clipboard_content(
    display: Display,
    window: Window,
    selection_atom: int,
    deferred_events: list["Event"],
    x11_event: "asyncio.Event",
    incr_atom: int,
) -> bytes | None:
    """Read clipboard content from the current selection owner.

    Requests UTF8_STRING target from the current clipboard owner and returns
    the content bytes. Uses asyncio.wait_for with CLIPBOARD_TIMEOUT to prevent
    hangs when the clipboard owner is unresponsive.

    Args:
        display: The X11 display connection.
        window: The window to receive selection data.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY).
        deferred_events: List to collect events deferred during polling.
        x11_event: asyncio.Event to signal when events are deferred.
        incr_atom: The INCR atom for detecting incremental transfers.

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
        content = await _wait_for_selection(
            display, window, prop_atom, deferred_events, x11_event, incr_atom
        )
        return content

    except asyncio.TimeoutError:
        logger.debug("Clipboard read timed out after %s seconds", CLIPBOARD_TIMEOUT)
        return None
    except Exception as e:
        logger.debug("Clipboard read failed: %s", e)
        return None


async def _wait_for_selection(
    display: "Display",
    window: "Window",
    prop_atom: int,
    deferred_events: list["Event"],
    x11_event: "asyncio.Event",
    incr_atom: int,
) -> bytes | None:
    """Wait for SelectionNotify and read property data.
    
    Uses wait_for_event_type to poll for SelectionNotify, with asyncio
    timeout handling. Signals x11_event if events were deferred.
    
    Args:
        display: The X11 display connection.
        window: The window that requested the selection.
        prop_atom: The property atom where data will be stored.
        deferred_events: List to collect events deferred during polling.
        x11_event: asyncio.Event to signal when events are deferred.
        incr_atom: The INCR atom for detecting incremental transfers.
    
    Returns:
        Content bytes if successful, None on failure/timeout.
    """
    import asyncio
    import logging
    
    from Xlib import X
    
    from pclipsync.selection_utils import wait_for_event_type
    
    logger = logging.getLogger(__name__)
    
    try:
        _ = await asyncio.wait_for(
            asyncio.to_thread(
                wait_for_event_type, display, X.SelectionNotify, deferred_events, CLIPBOARD_TIMEOUT
            ),
            timeout=CLIPBOARD_TIMEOUT,
        )
        # Signal main loop if events were deferred
        if deferred_events:
            x11_event.set()
        result = _read_selection_property(display, window, prop_atom, incr_atom)
        # For now, extract content from result (INCR handling in Phase 60)
        return result.content
    except asyncio.TimeoutError:
        # Signal main loop if events were deferred
        if deferred_events:
            x11_event.set()
        logger.debug("Timeout waiting for SelectionNotify")
        return None


def _read_selection_property(
    display: "Display", window: "Window", prop_atom: int, incr_atom: int
) -> PropertyReadResult:
    """Read and delete selection property from window.
    
    Args:
        display: The X11 display connection.
        window: The window containing the property.
        prop_atom: The property atom to read.
        incr_atom: The INCR atom for detecting incremental transfers.
    
    Returns:
        PropertyReadResult with content, INCR status, or failure state.
    """
    import logging
    
    from Xlib import X
    
    logger = logging.getLogger(__name__)
    
    try:
        prop = window.get_full_property(prop_atom, X.AnyPropertyType)
        
        if prop is None:
            logger.debug("Selection property was empty")
            return PropertyReadResult(content=None, is_incr=False)
        
        # Check for INCR transfer indication
        if prop.property_type == incr_atom:
            # DON'T delete property - caller handles deletion as handshake signal
            estimated_size = int.from_bytes(bytes(prop.value), byteorder="little")
            logger.debug("INCR transfer detected, estimated size: %d", estimated_size)
            return PropertyReadResult(content=None, is_incr=True, estimated_size=estimated_size)

        # Normal content - delete property and return content
        window.delete_property(prop_atom)
        display.flush()

        data = prop.value
        if isinstance(data, str):
            return PropertyReadResult(content=data.encode("utf-8"), is_incr=False)
        return PropertyReadResult(content=bytes(data), is_incr=False)
    except Exception as e:
        logger.debug("Failed to read selection property: %s", e)
        return PropertyReadResult(content=None, is_incr=False)


def _read_chunk_property(
    display: "Display", window: "Window", prop_atom: int
) -> bytes | None:
    """Read and delete a single INCR chunk property.

    Simple property reader for INCR chunks. Returns the raw bytes from
    the property, or empty bytes for zero-length chunk (end marker).
    Does NOT check for INCR type (already handled upstream).

    Args:
        display: The X11 display connection.
        window: The window containing the property.
        prop_atom: The property atom to read.

    Returns:
        Chunk bytes (may be empty for end marker), or None on failure.
    """
    import logging

    from Xlib import X

    logger = logging.getLogger(__name__)

    try:
        prop = window.get_full_property(prop_atom, X.AnyPropertyType)
        window.delete_property(prop_atom)
        display.flush()

        if prop is None:
            # Zero-length chunk signals end of INCR transfer
            return b""

        data = prop.value
        if isinstance(data, str):
            return data.encode("utf-8")
        return bytes(data)
    except Exception as e:
        logger.debug("Failed to read chunk property: %s", e)
        return None


def _handle_incr_transfer(
    display: "Display",
    window: "Window",
    prop_atom: int,
    deferred_events: list["Event"],
    chunk_timeout: float,
) -> bytes | None:
    """Handle INCR (incremental) clipboard transfer protocol.

    Accumulates chunked content from an INCR transfer. The caller must have
    already detected INCR (via _read_selection_property) and should call this
    to receive the actual content in chunks.

    The INCR protocol:
    1. Caller deletes property to signal readiness for first chunk
    2. Owner writes chunk data to property, sends PropertyNotify
    3. We read chunk, append to buffer, delete property
    4. Repeat until owner sends zero-length chunk (end marker)

    Args:
        display: The X11 display connection.
        window: The window receiving property changes.
        prop_atom: The property atom being used for transfer.
        deferred_events: List to collect events deferred during transfer.
        chunk_timeout: Timeout in seconds for each chunk.

    Returns:
        Complete content bytes on success, None on failure or timeout.
    """
    # Initial handshake: delete property to signal readiness for first chunk
    window.delete_property(prop_atom)
    display.flush()


    from pclipsync.selection_utils import wait_for_property_notify
    from pclipsync.protocol import MAX_CONTENT_SIZE
    import logging

    logger = logging.getLogger(__name__)

    buffer = bytearray()

    # Chunk accumulation loop
    while True:
        # Wait for owner to write next chunk (PropertyNotify)
        event = wait_for_property_notify(
            display, window, prop_atom, deferred_events, chunk_timeout
        )
        if event is None:
            # Timeout waiting for chunk - abort transfer
            logger.warning("INCR chunk timeout after %.1fs", chunk_timeout)
            return None

        # Read chunk data
        chunk = _read_chunk_property(display, window, prop_atom)
        if chunk is None:
            # Read failure - abort transfer
            return None

        # Zero-length chunk signals end of transfer
        if len(chunk) == 0:
            return bytes(buffer)

        # Append chunk to buffer
        buffer.extend(chunk)

        # Check accumulated size against limit
        if len(buffer) > MAX_CONTENT_SIZE:
            logger.warning(
                "INCR transfer exceeds %d bytes limit, aborting", MAX_CONTENT_SIZE
            )
            return None
