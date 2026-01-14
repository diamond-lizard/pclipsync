#!/usr/bin/env python3
"""Tests for _read_selection_property function."""
from unittest.mock import MagicMock

import pytest


class TestReadSelectionProperty:
    """Tests for _read_selection_property function."""

    def test_normal_utf8_string_response(self) -> None:
        """Normal UTF8_STRING response returns content in PropertyReadResult."""
        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456

        mock_prop = MagicMock()
        mock_prop.property_type = 789
        mock_prop.value = b"test content"
        mock_window.get_full_property.return_value = mock_prop

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content == b"test content"
        assert result.is_incr is False
        assert result.estimated_size == 0

        mock_window.delete_property.assert_called_once_with(prop_atom)
        mock_display.flush.assert_called_once()

    def test_incr_response_detection(self) -> None:
        """INCR response returns is_incr=True with estimated_size."""
        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456

        mock_prop = MagicMock()
        mock_prop.property_type = incr_atom
        estimated_size = 1048576
        mock_prop.value = estimated_size.to_bytes(4, byteorder="little")
        mock_window.get_full_property.return_value = mock_prop

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content is None
        assert result.is_incr is True
        assert result.estimated_size == estimated_size

        mock_window.delete_property.assert_not_called()

    def test_empty_property_returns_failure_result(self) -> None:
        """Empty/None property returns PropertyReadResult with content=None."""
        from pclipsync.clipboard_io import _read_selection_property, PropertyReadResult

        mock_display = MagicMock()
        mock_window = MagicMock()
        prop_atom = 123
        incr_atom = 456

        mock_window.get_full_property.return_value = None

        result = _read_selection_property(mock_display, mock_window, prop_atom, incr_atom)

        assert isinstance(result, PropertyReadResult)
        assert result.content is None
        assert result.is_incr is False
        assert result.estimated_size == 0
