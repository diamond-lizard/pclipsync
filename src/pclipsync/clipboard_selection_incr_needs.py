"""INCR transfer threshold detection.

This module provides functions to determine whether content exceeds
the X11 maximum property size and requires INCR transfer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pclipsync.clipboard_selection_incr_state import INCR_SAFETY_MARGIN

if TYPE_CHECKING:
    from Xlib.display import Display


def get_max_property_size(display: "Display") -> int:
    """Return the maximum property size in bytes for a single change_property.

    The X11 protocol limits property writes based on max_request_length.
    This function calculates the threshold above which INCR must be used.
    A safety margin is applied to avoid edge cases.

    Args:
        display: The X11 display connection.

    Returns:
        Maximum safe property size in bytes.
    """
    # max_request_length is in 4-byte units; multiply by 4 for bytes
    # Apply safety margin to avoid edge cases near the limit
    max_bytes = display.info.max_request_length * 4  # type: ignore[attr-defined]
    return int(max_bytes * INCR_SAFETY_MARGIN)


def needs_incr_transfer(content: bytes, display: "Display") -> bool:
    """Check if content is too large for a single change_property.

    Returns True if the content length exceeds the maximum property size
    threshold, meaning INCR protocol must be used for the transfer.

    Args:
        content: The content bytes to check.
        display: The X11 display connection.

    Returns:
        True if INCR transfer is needed, False otherwise.
    """
    return len(content) > get_max_property_size(display)
