#!/usr/bin/env python3
"""
Unit tests for HashState basic operations.

Tests HashState initialization, should_send logic, record_sent/received,
and clear methods.
"""
from pclipsync.hashing import HashState


def test_hashstate_initial_values() -> None:
    """Test HashState initializes with None hashes."""
    state = HashState()
    assert state.last_sent_hash is None
    assert state.last_received_hash is None


def test_hashstate_should_send_new_content() -> None:
    """Test should_send returns True for new content."""
    state = HashState()
    assert state.should_send("abc123") is True


def test_hashstate_should_send_false_for_duplicate() -> None:
    """Test should_send returns False when hash matches last_sent_hash."""
    state = HashState()
    state.last_sent_hash = "abc123"
    assert state.should_send("abc123") is False


def test_hashstate_should_send_false_for_echo() -> None:
    """Test should_send returns False when hash matches last_received_hash."""
    state = HashState()
    state.last_received_hash = "abc123"
    assert state.should_send("abc123") is False


def test_hashstate_record_sent() -> None:
    """Test record_sent updates last_sent_hash."""
    state = HashState()
    state.record_sent("abc123")
    assert state.last_sent_hash == "abc123"


def test_hashstate_record_received() -> None:
    """Test record_received updates last_received_hash."""
    state = HashState()
    state.record_received("abc123")
    assert state.last_received_hash == "abc123"


def test_hashstate_clear() -> None:
    """Test clear resets both hashes to None."""
    state = HashState()
    state.last_sent_hash = "sent123"
    state.last_received_hash = "recv456"
    state.clear()
    assert state.last_sent_hash is None
    assert state.last_received_hash is None


def test_hashstate_clear_received_hash() -> None:
    """Test clear_received_hash resets only last_received_hash to None."""
    state = HashState()
    state.last_sent_hash = "sent123"
    state.last_received_hash = "recv456"
    state.clear_received_hash()
    assert state.last_sent_hash == "sent123"
    assert state.last_received_hash is None


def test_hashstate_clear_sent_hash() -> None:
    """Test clear_sent_hash resets only last_sent_hash to None."""
    state = HashState()
    state.last_sent_hash = "sent123"
    state.last_received_hash = "recv456"
    state.clear_sent_hash()
    assert state.last_sent_hash is None
    assert state.last_received_hash == "recv456"
