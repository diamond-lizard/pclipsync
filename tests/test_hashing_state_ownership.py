#!/usr/bin/env python3
"""
Unit tests for HashState ownership loss behavior.

These are regression tests for bugs where stale hash state blocked
legitimate sends after clipboard ownership changed.
"""
from pclipsync.hashing import HashState


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
