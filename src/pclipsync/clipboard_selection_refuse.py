"""Selection request refusal utility.

This module provides a helper function to refuse SelectionRequest events
by sending a SelectionNotify with property=None.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest


def refuse_selection_request(event: "SelectionRequest", display: "Display") -> None:
    """Refuse a SelectionRequest by sending property=None.

    Sends a SelectionNotify event to the requestor indicating the request
    cannot be fulfilled by setting property to X.NONE.

    Args:
        event: The SelectionRequest event to refuse.
        display: The X11 display connection.
    """
    from Xlib import X
    from Xlib.protocol.event import SelectionNotify as SelectionNotifyEvent
    event.requestor.send_event(
        SelectionNotifyEvent(
            time=event.time,
            requestor=event.requestor.id,
            selection=event.selection,
            target=event.target,
            property=X.NONE,
        ),
        event_mask=0,
    )
    display.flush()
