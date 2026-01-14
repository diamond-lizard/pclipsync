#!/usr/bin/env python3
"""Shared fixtures for server handler tests."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def mock_state() -> MagicMock:
    """Create a mock ClipboardState."""
    state = MagicMock()
    state.hash_state = HashState()
    state.display = MagicMock()
    state.window = MagicMock()
    state.current_content = b""
    state.pending_incr_sends = {}
    return state


@pytest.fixture
def mock_writer() -> AsyncMock:
    """Create a mock StreamWriter."""
    writer = AsyncMock()
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    return writer


@pytest.fixture
def mock_shutdown_event() -> MagicMock:
    """Create a mock shutdown event."""
    return MagicMock()
