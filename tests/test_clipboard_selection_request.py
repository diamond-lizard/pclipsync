#!/usr/bin/env python3
"""Tests for clipboard selection request handling."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_display() -> MagicMock:
    """Create a mock X11 display."""
    display = MagicMock()
    # Return distinct atom values for each interned atom
    atom_map = {"TARGETS": 100, "UTF8_STRING": 101, "TIMESTAMP": 102}
    display.intern_atom.side_effect = lambda name: atom_map.get(name, 999)
    display.info.max_request_length = 65536  # Large enough for small content
    return display


@pytest.fixture
def mock_event() -> MagicMock:
    """Create a mock SelectionRequest event."""
    event = MagicMock()
    event.requestor = MagicMock()
    event.requestor.id = 12345
    event.property = 200
    event.selection = 300
    event.time = 987654321
    return event


def test_targets_includes_timestamp(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TARGETS response includes TIMESTAMP atom."""
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TARGETS (use mock_display.intern_atom return value)
    mock_event.target = 100  # TARGETS atom from fixture

    handle_selection_request(mock_display, mock_event, b"test content", None, {}, 0)

    # Verify change_property was called with targets list including TIMESTAMP
    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    targets_list = call_args[0][3]  # Fourth positional arg is the data
    # Check TIMESTAMP atom (102 from fixture) is in targets list
    assert 102 in targets_list


def test_timestamp_request_returns_integer(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request returns acquisition_time as 32-bit INTEGER."""
    from Xlib import Xatom
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TIMESTAMP
    mock_event.target = 102  # TIMESTAMP atom

    handle_selection_request(mock_display, mock_event, b"test content", 555666777, {}, 0)

    # Verify change_property was called with INTEGER type and acquisition_time
    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    prop_type = call_args[0][1]  # Second positional arg is property type
    format_bits = call_args[0][2]  # Third positional arg is format (32-bit)
    data = call_args[0][3]  # Fourth positional arg is the data
    assert prop_type == Xatom.INTEGER
    assert format_bits == 32
    assert data == [555666777]


def test_timestamp_request_has_valid_property(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request results in SelectionNotify with valid property."""
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 102  # TIMESTAMP atom
    original_property = mock_event.property

    handle_selection_request(mock_display, mock_event, b"test content", 555666777, {}, 0)

    # Property should NOT be set to X.NONE (which would indicate refusal)
    # The original property value should be preserved
    assert mock_event.property == original_property

    # Verify SelectionNotify was sent
    mock_event.requestor.send_event.assert_called_once()
