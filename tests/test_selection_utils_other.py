#!/usr/bin/env python3
"""Tests for get_other_selection function.

Uses mocks for X11 display to avoid requiring a real display.
"""

from Xlib import Xatom

from pclipsync.selection_utils import get_other_selection


class TestGetOtherSelection:
    """Tests for get_other_selection function."""

    def test_clipboard_returns_primary(self) -> None:
        """When selection is CLIPBOARD, return PRIMARY."""
        clipboard_atom = 123  # Arbitrary non-PRIMARY value
        result = get_other_selection(clipboard_atom, clipboard_atom)
        assert result == Xatom.PRIMARY

    def test_primary_returns_clipboard(self) -> None:
        """When selection is PRIMARY, return CLIPBOARD."""
        clipboard_atom = 123
        result = get_other_selection(Xatom.PRIMARY, clipboard_atom)
        assert result == clipboard_atom

    def test_other_atom_returns_clipboard(self) -> None:
        """When selection is neither CLIPBOARD nor PRIMARY, return CLIPBOARD."""
        clipboard_atom = 123
        other_atom = 456
        result = get_other_selection(other_atom, clipboard_atom)
        assert result == clipboard_atom
