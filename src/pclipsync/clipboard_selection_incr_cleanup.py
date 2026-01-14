"""INCR transfer cleanup functions.

This module provides functions to clean up stale or cancelled INCR transfers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pclipsync.clipboard_selection_incr_state import INCR_SEND_TIMEOUT

if TYPE_CHECKING:
    from Xlib.display import Display
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def cleanup_stale_incr_sends(
    display: "Display",
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Remove INCR send transfers that have exceeded the timeout.

    Iterates over a snapshot of pending_incr_sends to avoid RuntimeError
    from modifying dict during iteration. For each stale transfer, logs
    a warning and calls unsubscribe_incr_requestor to clean up.

    Args:
        display: The X11 display connection.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import time
    import logging
    from pclipsync.clipboard_selection_incr_subscribe import unsubscribe_incr_requestor
    logger = logging.getLogger(__name__)

    current_time = time.time()
    for key, state in list(pending_incr_sends.items()):
        elapsed = current_time - state.start_time
        if elapsed > INCR_SEND_TIMEOUT:
            logger.warning("INCR send: transfer timed out after %.1f seconds: %s",
                elapsed, key)
            unsubscribe_incr_requestor(display, state, key, pending_incr_sends)


def cleanup_incr_sends_on_ownership_loss(
    display: "Display",
    selection_atom: int,
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Clean up INCR send transfers when losing selection ownership.

    When we lose ownership of a selection, any pending INCR transfers for
    that selection are no longer valid (the content we were serving may
    have changed). Collects matching entries into a list first to avoid
    modifying dict during iteration.

    Args:
        display: The X11 display connection.
        selection_atom: The selection atom we lost ownership of.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import logging
    from pclipsync.clipboard_selection_incr_subscribe import unsubscribe_incr_requestor
    logger = logging.getLogger(__name__)

    keys_to_remove = [
        key for key, state in pending_incr_sends.items()
        if state.selection_atom == selection_atom
    ]

    for key in keys_to_remove:
        state = pending_incr_sends[key]
        logger.debug("INCR send: ownership lost, canceling transfer: %s", key)
        unsubscribe_incr_requestor(display, state, key, pending_incr_sends)
