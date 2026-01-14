"""INCR transfer initiation.

This module provides the function to initiate an INCR transfer for
large clipboard content that exceeds the maximum property size.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.protocol.event import SelectionRequest
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def initiate_incr_send(
    display: "Display",
    event: "SelectionRequest",
    content: bytes,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
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
    from pclipsync.clipboard_selection_incr_subscribe import unsubscribe_requestor_events
    from pclipsync.clipboard_selection_refuse import refuse_selection_request

    # Subscribe to PropertyNotify and StructureNotify on requestor window
    event.requestor.change_attributes(
        event_mask=X.PropertyChangeMask | X.StructureNotifyMask
    )

    try:
        _write_incr_and_notify(event, incr_atom, content, pending_incr_sends, display)
    except Exception:
        unsubscribe_requestor_events(display, event.requestor)
        refuse_selection_request(event, display)
        raise


def _write_incr_and_notify(
    event: "SelectionRequest",
    incr_atom: int,
    content: bytes,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
    display: "Display",
) -> None:
    """Write INCR property, create state, and send SelectionNotify."""
    import logging
    import time
    from Xlib.protocol.event import SelectionNotify as SelectionNotifyEvent
    from pclipsync.clipboard_selection_incr_state import IncrSendState as ISS
    logger = logging.getLogger(__name__)

    event.requestor.change_property(event.property, incr_atom, 32, [len(content)])

    transfer_key = (event.requestor.id, event.property)
    pending_incr_sends[transfer_key] = ISS(
        requestor=event.requestor,
        property_atom=event.property,
        target_atom=event.target,
        selection_atom=event.selection,
        content=content,
        offset=0,
        start_time=time.time(),
    )

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
