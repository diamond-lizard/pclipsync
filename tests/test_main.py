"""Tests for CLI argument handling in main.py."""
import pytest
from click.testing import CliRunner

from pclipsync.main import main


class TestCLIArguments:
    """Tests for command-line argument validation."""

    def test_no_mode_specified_exits_with_code_2(self):
        """Test that missing --server or --client gives usage error."""
        runner = CliRunner()
        result = runner.invoke(main, ["--socket", "/tmp/test.sock"])
        assert result.exit_code == 2
        assert "must be specified" in result.output

    def test_both_modes_specified_exits_with_code_2(self):
        """Test that both --server and --client gives usage error."""
        runner = CliRunner()
        result = runner.invoke(main, ["--server", "--client", "--socket", "/tmp/test.sock"])
        assert result.exit_code == 2
        assert "mutually exclusive" in result.output

    def test_missing_socket_exits_with_code_2(self):
        """Test that missing --socket gives usage error."""
        runner = CliRunner()
        result = runner.invoke(main, ["--server"])
        assert result.exit_code == 2
        assert "socket" in result.output.lower()

    def test_help_exits_with_code_0(self):
        """Test that --help exits cleanly with code 0."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "server" in result.output.lower()
        assert "client" in result.output.lower()
