#!/usr/bin/env python3
"""Additional tests for clipboard selection request handling."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_display() -> MagicMock:
    """Create a mock X11 display."""
    display = MagicMock()
    atom_map = {"TARGETS": 100, "UTF8_STRING": 101, "TIMESTAMP": 102}
    display.intern_atom.side_effect = lambda name: atom_map.get(name, 999)
    display.display.info.max_request_length = 65536  # Large enough for small content
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


def test_utf8_string_still_works(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Regression test: UTF8_STRING requests still work correctly."""
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 101  # UTF8_STRING atom
    content = b"test clipboard content"

    handle_selection_request(mock_display, mock_event, content, None, {}, 0)

    mock_event.requestor.change_property.assert_called_once()
    call_args = mock_event.requestor.change_property.call_args
    prop_type = call_args[0][1]
    format_bits = call_args[0][2]
    data = call_args[0][3]
    assert prop_type == 101  # UTF8_STRING
    assert format_bits == 8
    assert data == content


def test_unsupported_target_refused(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Regression test: unsupported targets are still refused."""
    from Xlib import X
    from pclipsync.clipboard_selection import handle_selection_request

    mock_event.target = 999  # Unknown target

    handle_selection_request(mock_display, mock_event, b"test", None, {}, 0)

    # Property should be set to X.NONE
    assert mock_event.property == X.NONE


def test_timestamp_refused_when_acquisition_time_none(
    mock_display: MagicMock, mock_event: MagicMock
) -> None:
    """Test TIMESTAMP request refused when acquisition_time is None."""
    from Xlib import X
    from pclipsync.clipboard_selection import handle_selection_request

    # Request TIMESTAMP
    mock_event.target = 102  # TIMESTAMP atom

    handle_selection_request(mock_display, mock_event, b"test", None, {}, 0)

    # Property should be set to X.NONE (refused)
    assert mock_event.property == X.NONE
    # change_property should NOT be called
    mock_event.requestor.change_property.assert_not_called()
