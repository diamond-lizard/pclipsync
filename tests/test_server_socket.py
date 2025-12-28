#!/usr/bin/env python3
"""
Tests for server socket utilities.

Tests check_socket_state for stale vs active sockets, print_startup_message
output, and cleanup_socket behavior.
"""
import os
import socket
import tempfile

import pytest

from pclipsync.server_socket import check_socket_state, cleanup_socket, print_startup_message


class TestCheckSocketState:
    """Tests for check_socket_state function."""

    def test_no_socket_file_returns_immediately(self) -> None:
        """Test check_socket_state returns when socket file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = os.path.join(tmpdir, "nonexistent.sock")
            # Should not raise
            check_socket_state(socket_path)

    def test_stale_socket_is_unlinked(self) -> None:
        """Test check_socket_state unlinks stale socket file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = os.path.join(tmpdir, "stale.sock")
            # Create a socket file but don't listen on it
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(socket_path)
            sock.close()

            assert os.path.exists(socket_path)
            check_socket_state(socket_path)
            assert not os.path.exists(socket_path)

    def test_active_socket_exits_with_error(self) -> None:
        """Test check_socket_state exits when socket is active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = os.path.join(tmpdir, "active.sock")
            # Create and listen on socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(socket_path)
            sock.listen(1)

            try:
                with pytest.raises(SystemExit) as exc_info:
                    check_socket_state(socket_path)
                assert exc_info.value.code == 1
            finally:
                sock.close()


class TestPrintStartupMessage:
    """Tests for print_startup_message function."""

    def test_prints_socket_path(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_startup_message prints socket path to stderr."""
        print_startup_message("/path/to/socket")
        captured = capsys.readouterr()
        assert "Listening on /path/to/socket" in captured.err

    def test_prints_ssh_forward_example(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_startup_message prints SSH forward example."""
        print_startup_message("/path/to/socket")
        captured = capsys.readouterr()
        assert "ssh -R REMOTE_SOCKET_PATH:/path/to/socket" in captured.err


class TestCleanupSocket:
    """Tests for cleanup_socket function."""

    def test_removes_existing_socket(self) -> None:
        """Test cleanup_socket removes existing socket file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = os.path.join(tmpdir, "test.sock")
            # Create a file
            with open(socket_path, "w") as f:
                f.write("")
            assert os.path.exists(socket_path)
            cleanup_socket(socket_path)
            assert not os.path.exists(socket_path)

    def test_ignores_nonexistent_socket(self) -> None:
        """Test cleanup_socket doesn't raise for nonexistent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = os.path.join(tmpdir, "nonexistent.sock")
            # Should not raise
            cleanup_socket(socket_path)
