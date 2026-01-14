"""Selection request helper functions.

This module provides helper functions for handling specific SelectionRequest
target types and sending SelectionNotify responses.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def handle_targets_request(
    event: "SelectionRequest", targets_atom: int, utf8_atom: int, timestamp_atom: int
) -> None:
    """Return list of supported targets."""
    from Xlib import Xatom
    targets = [targets_atom, utf8_atom, Xatom.STRING, timestamp_atom]
    event.requestor.change_property(event.property, Xatom.ATOM, 32, targets)


def handle_content_request(
    event: "SelectionRequest", content: bytes, display: "Display",
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"], incr_atom: int,
) -> bool:
    """Return content - directly or via INCR. Returns True if needs own notify."""
    from pclipsync.clipboard_selection_incr_needs import needs_incr_transfer
    from pclipsync.clipboard_selection_incr_initiate import initiate_incr_send
    if not needs_incr_transfer(content, display):
        event.requestor.change_property(event.property, event.target, 8, content)
        return False  # Caller should send SelectionNotify
    initiate_incr_send(display, event, content, pending_incr_sends, incr_atom)
    return True  # INCR sends its own SelectionNotify


def handle_timestamp_request(
    event: "SelectionRequest", acquisition_time: int | None
) -> None:
    """Return acquisition timestamp as 32-bit integer."""
    from Xlib import X, Xatom
    logger = logging.getLogger(__name__)
    if acquisition_time is not None:
        event.requestor.change_property(
            event.property, Xatom.INTEGER, 32, [acquisition_time]
        )
        logger.debug("Handled TIMESTAMP request, returning time=%s", acquisition_time)
    else:
        event.property = X.NONE
        logger.debug("Refused TIMESTAMP request, no acquisition_time")


def send_selection_notify(event: "SelectionRequest", display: "Display") -> None:
    """Send SelectionNotify response."""
    from Xlib.protocol.event import SelectionNotify as SelectionNotifyEvent
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
