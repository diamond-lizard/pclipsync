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


def test_hashstate_clear_received_hash() -> None:
    """Test clear_received_hash resets only last_received_hash to None."""
    state = HashState()
    state.last_sent_hash = "sent123"
    state.last_received_hash = "recv456"
    state.clear_received_hash()
    assert state.last_sent_hash == "sent123"
    assert state.last_received_hash is None


def test_hashstate_ownership_loss_unblocks_previously_received_content() -> None:
    """
    Regression test for bug: content matching stale received hash was blocked.

    Scenario that caused the bug:
    1. Content with hash H is received from remote -> last_received_hash = H
    2. Another app takes clipboard ownership (we lose ownership)
    3. User copies content with hash H (matching old received hash)
    4. BUG: This was blocked as "echo" because last_received_hash still = H

    Fix: clear_received_hash() is called when ownership is lost, so step 3 succeeds.
    """
    state = HashState()

    # Step 1: Receive content with hash H from remote
    hash_h = "abc123def456"
    state.record_received(hash_h)
    assert state.last_received_hash == hash_h

    # Before fix: should_send(H) returns False - blocked as echo
    assert state.should_send(hash_h) is False

    # Step 2: Simulate ownership loss by calling clear_received_hash
    # (This is what sync_loop_inner.py does on SetSelectionOwnerNotify
    # when another app takes ownership)
    state.clear_received_hash()

    # Step 3: Now content with hash H should be sendable
    # Before fix: would still return False
    # After fix: returns True
    assert state.should_send(hash_h) is True


def test_hashstate_clear_sent_hash() -> None:
    """Test clear_sent_hash resets only last_sent_hash to None."""
    state = HashState()
    state.last_sent_hash = "sent123"
    state.last_received_hash = "recv456"
    state.clear_sent_hash()
    assert state.last_sent_hash is None
    assert state.last_received_hash == "recv456"


def test_hashstate_ownership_loss_unblocks_previously_sent_content() -> None:
    """
    Regression test for bug: content matching stale sent hash was blocked.

    Scenario that caused the bug (from logs 2026-01-10):
    1. Client sends 34 bytes to server with hash H -> last_sent_hash = H
    2. Server receives and sets clipboard, then another app reads it
    3. Later, another app takes clipboard ownership on client
    4. That app happens to have content with hash H (same as previously sent)
    5. BUG: Client blocked send as "duplicate" because last_sent_hash = H

    The key insight: once another application takes clipboard ownership,
    the content comes from that application - it's semantically new content,
    even if it happens to match something we previously sent.

    Fix: clear_sent_hash() is called when ownership is lost, so step 5 succeeds.
    """
    state = HashState()

    # Step 1: Send content with hash H to remote
    hash_h = "f60261fd10b7face"  # Actual hash from bug report
    state.record_sent(hash_h)
    assert state.last_sent_hash == hash_h

    # Before fix: should_send(H) returns False - blocked as duplicate
    assert state.should_send(hash_h) is False

    # Step 3-4: Another app takes ownership (simulated by clear_sent_hash)
    # This is what sync_loop_inner.py does on SetSelectionOwnerNotify
    # when another app takes ownership
    state.clear_sent_hash()

    # Step 5: Now content with hash H should be sendable
    # Before fix: would return False (blocked as duplicate)
    # After fix: returns True
    assert state.should_send(hash_h) is True
