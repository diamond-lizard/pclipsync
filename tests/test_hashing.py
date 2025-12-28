#!/usr/bin/env python3
"""
Unit tests for SHA-256 hashing and HashState loop prevention.

Tests compute_hash for consistent output and HashState for proper
duplicate/echo detection and state management.
"""
from pclipsync.hashing import HashState, compute_hash


def test_compute_hash_produces_sha256_hex() -> None:
    """Test compute_hash returns 64-character hex SHA-256 digest."""
    result = compute_hash(b"test content")
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_compute_hash_consistent_output() -> None:
    """Test same input always produces same hash."""
    data = b"Hello world!"
    hash1 = compute_hash(data)
    hash2 = compute_hash(data)
    assert hash1 == hash2


def test_compute_hash_different_for_different_input() -> None:
    """Test different inputs produce different hashes."""
    hash1 = compute_hash(b"content A")
    hash2 = compute_hash(b"content B")
    assert hash1 != hash2


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
