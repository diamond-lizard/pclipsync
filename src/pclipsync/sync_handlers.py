#!/usr/bin/env python3
"""Clipboard synchronization event handlers.

This module provides handlers for clipboard synchronization events:
- handle_clipboard_change: process local clipboard changes and send to remote
- handle_incoming_content: receive remote content and set local clipboard
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from Xlib import Xatom

from pclipsync.clipboard_events import set_clipboard_content
from pclipsync.clipboard_io import read_clipboard_content
from pclipsync.hashing import compute_hash
from pclipsync.protocol import encode_netstring, validate_content_size

if TYPE_CHECKING:
    from pclipsync.sync_state import ClipboardState

logger = logging.getLogger(__name__)


async def handle_clipboard_change(
    state: ClipboardState,
    writer: asyncio.StreamWriter,
    selection_atom: int,
) -> None:
    """Handle local clipboard change and send to remote.

    Called when XFixesSelectionNotify is received. Reads clipboard content,
    computes hash, checks for duplicates/echoes, and sends if appropriate.

    Args:
        state: The clipboard synchronization state.
        writer: The asyncio StreamWriter for the socket connection.
        selection_atom: The selection atom (CLIPBOARD or PRIMARY) that changed.
    """
    # Skip if we own the selection (we just set it from remote content)
    owner = state.display.get_selection_owner(selection_atom)
    if owner == state.window:
        logger.debug("We own selection, skipping read")
        return
    
    content = await read_clipboard_content(state.display, state.window, selection_atom)
    if content is None or len(content) == 0:
        logger.debug("Clipboard read returned empty/None, skipping")
        return

    if not validate_content_size(content):
        logger.warning("Clipboard content exceeds 10 MB limit, skipping")
        return

    current_hash = compute_hash(content)
    if not state.hash_state.should_send(current_hash):
        logger.debug("Skipping duplicate or echo content")
        return

    encoded = encode_netstring(content)
    writer.write(encoded)
    await writer.drain()
    state.hash_state.record_sent(current_hash)
    logger.debug("Sent %d bytes to remote", len(content))


async def handle_incoming_content(
    state: ClipboardState, content: bytes
) -> None:
    """Handle incoming content from remote and set local clipboard.

    Computes hash and records it BEFORE setting clipboard to prevent
    the resulting XFixes event from triggering an echo. Updates both
    CLIPBOARD and PRIMARY selections.

    Args:
        state: The clipboard synchronization state.
        content: The raw clipboard content bytes from remote.
    """
    # Record hash BEFORE setting clipboard to prevent echo
    content_hash = compute_hash(content)
    state.hash_state.record_received(content_hash)
    state.current_content = content

    # Get atoms for both selections
    clipboard_atom = state.display.intern_atom("CLIPBOARD")
    primary_atom = Xatom.PRIMARY

    # Set both CLIPBOARD and PRIMARY selections
    if not set_clipboard_content(state.display, state.window, content, clipboard_atom):
        logger.error("Failed to set CLIPBOARD selection")
    if not set_clipboard_content(state.display, state.window, content, primary_atom):
        logger.error("Failed to set PRIMARY selection")

    logger.debug("Received and set %d bytes from remote", len(content))
