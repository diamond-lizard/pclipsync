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
from pclipsync.selection_utils import get_other_selection, get_server_timestamp

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
    
    content = await read_clipboard_content(
        state.display, state.window, selection_atom,
        state.deferred_events, state.x11_event, state.incr_atom
    )
    if content is None or len(content) == 0:
        logger.debug("Clipboard read returned empty/None, skipping")
        return

    if not validate_content_size(content):
        logger.warning("Clipboard content exceeds 10 MB limit, skipping")
        return

    # Update current_content so we can serve this if we take ownership
    state.current_content = content

    # Mirror to other selection before sending to remote
    other_atom = get_other_selection(selection_atom, state.clipboard_atom)
    if set_clipboard_content(state.display, state.window, content, other_atom):
        state.owned_selections.add(other_atom)
        state.acquisition_time = get_server_timestamp(
            state.display, state.window, state.deferred_events
        )
    else:
        logger.warning("Failed to mirror to other selection, continuing")
    current_hash = compute_hash(content)
    if not state.hash_state.should_send(current_hash):
        sent = state.hash_state.last_sent_hash
        recv = state.hash_state.last_received_hash
        logger.debug(
            "Skipping duplicate or echo: hash=%s sent=%s recv=%s",
            current_hash[:16], sent[:16] if sent else None, recv[:16] if recv else None)
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


    # Clear owned_selections - we're claiming new ownership of both selections
    state.owned_selections.clear()
    # Get atoms for both selections
    clipboard_atom = state.clipboard_atom
    primary_atom = Xatom.PRIMARY

    # Set both CLIPBOARD and PRIMARY selections
    if set_clipboard_content(state.display, state.window, content, clipboard_atom):
        state.owned_selections.add(clipboard_atom)
    else:
        logger.error("Failed to set CLIPBOARD selection")
    if set_clipboard_content(state.display, state.window, content, primary_atom):
        state.owned_selections.add(primary_atom)
    else:
        logger.error("Failed to set PRIMARY selection")

    # Set acquisition_time if we own at least one selection
    if state.owned_selections:
        state.acquisition_time = get_server_timestamp(
            state.display, state.window, state.deferred_events
        )

    logger.debug("Received and set %d bytes from remote", len(content))
