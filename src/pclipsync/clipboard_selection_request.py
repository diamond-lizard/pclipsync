"""Selection request handling.

This module provides the function to respond to SelectionRequest events
when owning clipboard selections.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def handle_selection_request(
    display: "Display",
    event: "SelectionRequest",
    content: bytes,
    acquisition_time: int | None,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
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
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
        incr_atom: The INCR atom for type field.
    """
    from Xlib import X, Xatom
    import logging
    from pclipsync.clipboard_selection_request_helpers import (
        handle_targets_request, handle_content_request,
        handle_timestamp_request, send_selection_notify,
    )
    logger = logging.getLogger(__name__)

    targets_atom = display.intern_atom("TARGETS")
    utf8_atom = display.intern_atom("UTF8_STRING")
    timestamp_atom = display.intern_atom("TIMESTAMP")
    logger.debug("SelectionRequest target=%s targets=%s utf8=%s STRING=%s ts=%s",
        event.target, targets_atom, utf8_atom, Xatom.STRING, timestamp_atom)

    if event.target == targets_atom:
        handle_targets_request(event, targets_atom, utf8_atom, timestamp_atom)
    elif event.target in (utf8_atom, Xatom.STRING):
        incr_handled = handle_content_request(
            event, content, display, pending_incr_sends, incr_atom
        )
        if incr_handled:
            return  # INCR sends its own SelectionNotify
    elif event.target == timestamp_atom:
        handle_timestamp_request(event, acquisition_time)
    else:
        event.property = X.NONE

    send_selection_notify(event, display)
