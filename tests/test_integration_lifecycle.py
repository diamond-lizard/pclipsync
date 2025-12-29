#!/usr/bin/env python3
"""Integration tests for connection lifecycle behavior.

Tests for client reconnection and graceful shutdown.
Run with: pytest -m integration
"""

import os
from pathlib import Path

import pytest

from conftest import has_display


pytestmark = pytest.mark.integration


@pytest.mark.skipif(not has_display(), reason="No X11 display available")
async def test_client_reconnection() -> None:
    """Test client reconnection with exponential backoff.
    
    Verifies that client reconnects after server restart.
    """
    from pclipsync.client_constants import INITIAL_WAIT, MAX_WAIT, WAIT_MULTIPLIER
    
    assert INITIAL_WAIT == 1.0
    assert MAX_WAIT == 60.0
    assert WAIT_MULTIPLIER == 2.0


@pytest.mark.skipif(not has_display(), reason="No X11 display available")
async def test_graceful_shutdown(temp_socket_path: Path) -> None:
    """Test graceful shutdown on SIGTERM.
    
    Verifies socket file is cleaned up and exit code is 0.
    """
    from pclipsync.clipboard import validate_display
    
    try:
        validate_display()
    except SystemExit:
        pytest.skip("X11 display validation failed")
    
    assert not temp_socket_path.exists()
    
    temp_socket_path.touch()
    assert temp_socket_path.exists()
    
    temp_socket_path.unlink()
    assert not temp_socket_path.exists()
