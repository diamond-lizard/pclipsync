#!/usr/bin/env python3
"""Clipboard synchronization state.

This module provides the ClipboardState dataclass that groups all state
needed for bidirectional clipboard synchronization between server and
client modes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pclipsync.hashing import HashState

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.xobject.drawable import Window


@dataclass
class ClipboardState:
    """State for clipboard synchronization.

    Groups all state needed for bidirectional clipboard sync including
    the X11 display and window handles, hash state for loop prevention,
    and the current clipboard content.

    Attributes:
        display: The X11 display connection.
        window: The hidden window for clipboard ownership.
        hash_state: Hash tracking for loop prevention.
        current_content: Last known clipboard content bytes.
        acquisition_time: X server timestamp when we acquired clipboard ownership,
            or None if we don't own it.
    """

    display: Display
    window: Window
    hash_state: HashState = field(default_factory=HashState)
    current_content: bytes = b""
    acquisition_time: int | None = None
