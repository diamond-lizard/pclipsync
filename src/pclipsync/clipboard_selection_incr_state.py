"""INCR transfer state and constants.

This module provides the IncrSendState dataclass for tracking in-progress
INCR send transfers, along with the constants used by the INCR protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.xobject.drawable import Window


# Safety margin for INCR threshold (90% of max)
INCR_SAFETY_MARGIN: float = 0.9

# Chunk size for INCR transfers (65536 bytes, well below typical max_request)
INCR_CHUNK_SIZE: int = 65536

# Maximum time to wait for INCR transfer completion (seconds)
INCR_SEND_TIMEOUT: float = 30.0


@dataclass
class IncrSendState:
    """State for an in-progress INCR send transfer.

    Tracks all information needed to send clipboard content in chunks
    via the INCR protocol when content exceeds the maximum property size.

    Attributes:
        requestor: The requestor window that requested the clipboard content.
        property_atom: The property atom where chunks should be written.
        target_atom: The target atom (e.g., UTF8_STRING) for the content type.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY).
        content: The full content bytes to send.
        offset: Current offset into content for the next chunk.
        start_time: Timestamp when the transfer started (for timeout).
        completion_sent: True if zero-length completion marker was sent.
    """

    requestor: Window
    property_atom: int
    target_atom: int
    selection_atom: int
    content: bytes
    offset: int
    start_time: float
    completion_sent: bool = False
