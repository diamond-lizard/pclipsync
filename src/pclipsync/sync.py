#!/usr/bin/env python3
"""Bidirectional clipboard synchronization coordination.

This module re-exports synchronization components from submodules for
convenient imports. The actual implementations are in:
- sync_state: ClipboardState dataclass
- sync_handlers: handle_clipboard_change, handle_incoming_content
- sync_loop: run_sync_loop
"""

from pclipsync.sync_handlers import handle_clipboard_change, handle_incoming_content
from pclipsync.sync_loop import run_sync_loop
from pclipsync.sync_state import ClipboardState

__all__ = [
    "ClipboardState",
    "handle_clipboard_change",
    "handle_incoming_content",
    "run_sync_loop",
]
