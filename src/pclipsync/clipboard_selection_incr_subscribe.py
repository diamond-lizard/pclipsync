"""INCR requestor event subscription management.

This module provides functions to unsubscribe from requestor window
events when INCR transfers complete or are cancelled.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.xobject.drawable import Window
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def unsubscribe_requestor_events(display: "Display", requestor: "Window") -> None:
    """Clear event masks on a requestor window.

    Removes PropertyNotify and StructureNotify event subscriptions from
    a requestor window. If the window was destroyed, the X11 error will
    be printed to stderr but will not raise a Python exception.

    Args:
        display: The X11 display connection.
        requestor: The requestor window to unsubscribe from.
    """
    requestor.change_attributes(event_mask=0)
    display.flush()


def unsubscribe_incr_requestor(
    display: "Display",
    state: "IncrSendState",
    transfer_key: tuple[int, int],
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Unsubscribe from requestor events and remove transfer entry.

    Checks if other INCR transfers exist for the same requestor window.
    If this is the last transfer for the window, clears event masks.
    Always removes the transfer entry from pending_incr_sends.

    Args:
        display: The X11 display connection.
        state: The IncrSendState for this transfer.
        transfer_key: The (requestor_id, property_atom) tuple identifying this transfer.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    requestor_id = transfer_key[0]

    # Count transfers for this requestor window
    count = sum(1 for key in pending_incr_sends if key[0] == requestor_id)

    if count == 1:
        # This is the last transfer for the window - unsubscribe
        unsubscribe_requestor_events(display, state.requestor)

    # Remove the transfer entry
    if transfer_key in pending_incr_sends:
        del pending_incr_sends[transfer_key]
