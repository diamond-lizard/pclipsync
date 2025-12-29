#!/usr/bin/env python3
"""Pytest fixtures for pclipsync tests.

Provides fixtures for X11 display setup, temporary socket paths,
and hash state initialization.
"""

import os
import subprocess
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from pclipsync.hashing import HashState


@pytest.fixture
def hash_state() -> HashState:
    """Create a fresh HashState instance for testing."""
    return HashState()


@pytest.fixture
def temp_socket_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide a temporary path for Unix domain socket testing."""
    socket_path = tmp_path / "test.sock"
    yield socket_path
    if socket_path.exists():
        socket_path.unlink()


@pytest.fixture
def xvfb_display() -> Generator[str | None, None, None]:
    """Start Xvfb virtual display if available, yield DISPLAY string.
    
    Returns None if Xvfb is not available. Tests using this fixture
    should skip if the value is None.
    """
    try:
        result = subprocess.run(
            ["which", "Xvfb"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            yield None
            return
    except FileNotFoundError:
        yield None
        return
    
    display_num = 99
    display = f":{display_num}"
    proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", "1024x768x24"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        import time
        
        time.sleep(0.5)
        if proc.poll() is not None:
            yield None
            return
        old_display = os.environ.get("DISPLAY")
        os.environ["DISPLAY"] = display
        yield display
        if old_display is not None:
            os.environ["DISPLAY"] = old_display
        elif "DISPLAY" in os.environ:
            del os.environ["DISPLAY"]
    finally:
        proc.terminate()
        proc.wait()
