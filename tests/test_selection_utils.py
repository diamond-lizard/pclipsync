#!/usr/bin/env python3
"""Tests for selection_utils module.

Tests for get_other_selection, wait_for_event_type, and get_server_timestamp.
Uses mocks for X11 display to avoid requiring a real display.
"""

from unittest.mock import MagicMock

from Xlib import X, Xatom

from pclipsync.selection_utils import get_other_selection, wait_for_event_type


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


class TestWaitForEventType:
    """Tests for wait_for_event_type function."""
    
    def test_returns_matching_event_immediately(self) -> None:
        """Return immediately when first event matches target type."""
        mock_display = MagicMock()
        mock_event = MagicMock()
        mock_event.type = X.SelectionNotify
        mock_display.next_event.return_value = mock_event
        
        deferred: list = []
        result = wait_for_event_type(mock_display, X.SelectionNotify, deferred)
        
        assert result == mock_event
        assert deferred == []
    
    def test_defers_selection_request_events(self) -> None:
        """Defer SelectionRequest events until target found."""
        mock_display = MagicMock()
        
        req_event = MagicMock()
        req_event.type = X.SelectionRequest
        
        target_event = MagicMock()
        target_event.type = X.PropertyNotify
        
        mock_display.next_event.side_effect = [req_event, target_event]
        
        deferred: list = []
        result = wait_for_event_type(mock_display, X.PropertyNotify, deferred)
        
        assert result == target_event
        assert deferred == [req_event]
    
    def test_defers_set_selection_owner_notify(self) -> None:
        """Defer SetSelectionOwnerNotify events until target found."""
        mock_display = MagicMock()
        
        owner_event = MagicMock()
        owner_event.type = 999  # Non-standard type
        type(owner_event).__name__ = "SetSelectionOwnerNotify"
        
        target_event = MagicMock()
        target_event.type = X.SelectionNotify
        
        mock_display.next_event.side_effect = [owner_event, target_event]
        
        deferred: list = []
        result = wait_for_event_type(mock_display, X.SelectionNotify, deferred)
        
        assert result == target_event
        assert deferred == [owner_event]
    
    def test_ignores_other_events(self) -> None:
        """Discard events that are not target or deferrable types."""
        mock_display = MagicMock()
        
        other_event = MagicMock()
        other_event.type = X.Expose  # Not deferrable
        type(other_event).__name__ = "Expose"
        
        target_event = MagicMock()
        target_event.type = X.SelectionNotify
        
        mock_display.next_event.side_effect = [other_event, target_event]
        
        deferred: list = []
        result = wait_for_event_type(mock_display, X.SelectionNotify, deferred)
        
        assert result == target_event
        assert deferred == []  # other_event was discarded, not deferred
