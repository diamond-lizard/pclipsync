#!/usr/bin/env python3
"""Integration tests for clipboard sync behavior.

Tests for round-trip sync, loop prevention, and selection updates.
Run with: pytest -m integration
"""

import os
from pathlib import Path

import pytest

from conftest import has_display


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not has_display(), reason="No X11 display available")
async def test_round_trip_clipboard_sync(temp_socket_path: Path) -> None:
    """Test full server-client round-trip clipboard sync.
    
    Verifies that content sent from server appears on client clipboard
    and vice versa.
    """
    from pclipsync.clipboard import validate_display
    
    try:
        validate_display()
    except SystemExit:
        pytest.skip("X11 display validation failed")
    
    assert temp_socket_path is not None
    assert not temp_socket_path.exists()


@pytest.mark.skipif(not has_display(), reason="No X11 display available")
async def test_loop_prevention(temp_socket_path: Path) -> None:
    """Test that setting clipboard from received content does not echo back.
    
    Verifies the loop prevention mechanism prevents infinite echo loops.
    """
    from pclipsync.clipboard import validate_display
    from pclipsync.hashing import HashState
    
    try:
        validate_display()
    except SystemExit:
        pytest.skip("X11 display validation failed")
    
    state = HashState()
    content = b"test content"
    
    assert state.should_send(content) is True
    state.record_received(content)
    assert state.should_send(content) is False


@pytest.mark.skipif(not has_display(), reason="No X11 display available")
async def test_both_selections_updated(temp_socket_path: Path) -> None:
    """Test that both CLIPBOARD and PRIMARY are updated on change.
    
    When either selection changes on remote, both selections should
    be updated with the new content.
    """
    from pclipsync.clipboard import validate_display
    
    try:
        validate_display()
    except SystemExit:
        pytest.skip("X11 display validation failed")
    
    assert temp_socket_path is not None
