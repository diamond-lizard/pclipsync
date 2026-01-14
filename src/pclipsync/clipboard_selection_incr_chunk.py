"""INCR chunk sending.

This module provides the function to send the next chunk of an INCR transfer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pclipsync.clipboard_selection_incr_state import INCR_CHUNK_SIZE

if TYPE_CHECKING:
    from Xlib.display import Display
    from pclipsync.clipboard_selection_incr_state import IncrSendState


def send_incr_chunk(
    display: "Display",
    state: "IncrSendState",
    transfer_key: tuple[int, int],
    pending_incr_sends: dict[tuple[int, int], "IncrSendState"],
) -> None:
    """Send the next chunk of an INCR transfer.

    Calculates and sends the next chunk of content based on current offset.
    If all content has been sent, writes a zero-length chunk to signal
    completion. Updates the offset in state after sending.

    Args:
        display: The X11 display connection.
        state: The IncrSendState for this transfer.
        transfer_key: The (requestor_id, property_atom) tuple identifying this transfer.
        pending_incr_sends: Dict tracking in-progress INCR send transfers.
    """
    import logging
    logger = logging.getLogger(__name__)

    content_length = len(state.content)

    if state.offset >= content_length:
        # All real data was sent - write zero-length completion marker
        state.requestor.change_property(
            state.property_atom, state.target_atom, 8, b""
        )
        display.flush()
        state.completion_sent = True
        logger.debug("INCR send complete: requestor=%s property=%s",
            transfer_key[0], transfer_key[1])
        return

    # Calculate next chunk
    chunk_end = min(state.offset + INCR_CHUNK_SIZE, content_length)
    chunk = state.content[state.offset:chunk_end]

    # Write chunk to requestor's property
    state.requestor.change_property(
        state.property_atom, state.target_atom, 8, chunk
    )
    display.flush()

    # Update offset
    state.offset = chunk_end
    logger.debug("INCR chunk sent: requestor=%s property=%s offset=%s/%s",
        transfer_key[0], transfer_key[1], state.offset, content_length)
