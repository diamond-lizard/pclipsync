"""X11 clipboard monitoring via XFixes extension.

This module provides functions for monitoring and manipulating X11 clipboard
selections (CLIPBOARD and PRIMARY) using the python-xlib library with the
XFixes extension. XFixes provides true event-driven notification when
clipboard ownership changes, avoiding the need for polling.

The module handles:
- Validating X11 display connectivity
- Creating hidden windows for clipboard ownership
- Registering for XFixesSelectionNotify events
"""

from __future__ import annotations

import os
import sys

from Xlib import X

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from Xlib.display import Display
    from Xlib.xobject.drawable import Window



def validate_display() -> Display:
    """Validate X11 connectivity and return Display object.

    Checks that the DISPLAY environment variable is set and opens an X11
    connection. This should be called at startup to fail fast if X11 is
    not available.

    Returns:
        Display object for X11 operations.

    Raises:
        SystemExit: If DISPLAY is unset or X11 connection fails.
    """
    display_name = os.environ.get("DISPLAY")
    if not display_name:
        print("Error: DISPLAY environment variable is not set.", file=sys.stderr)
        print("X11 display is required for clipboard access.", file=sys.stderr)
        sys.exit(1)

    try:
        from Xlib.display import Display as XDisplay
        return XDisplay(display_name)
    except Exception as e:
        print(f"Error: Failed to connect to X11 display: {e}", file=sys.stderr)
        sys.exit(1)


def get_display_fd(display: Display) -> int:
    """Get the file descriptor for the X11 display connection.

    The file descriptor can be integrated into asyncio's event loop using
    loop.add_reader() for event-driven X11 event processing.

    Args:
        display: The X11 display connection.

    Returns:
        File descriptor number for the display connection.
    """
    return display.fileno()


def create_hidden_window(display: Display) -> Window:
    """Create a 1x1 unmapped window for clipboard ownership.

    X11 clipboard ownership requires a window. This creates a minimal hidden
    window that can own selections when setting clipboard content from
    received data.

    Args:
        display: The X11 display connection.

    Returns:
        A Window object for owning clipboard selections.
    """
    screen = display.screen()
    window = screen.root.create_window(
        0, 0, 1, 1, 0, screen.root_depth, event_mask=X.PropertyChangeMask,
    )
    return window
