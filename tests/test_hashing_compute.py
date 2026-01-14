#!/usr/bin/env python3
"""
Unit tests for compute_hash SHA-256 function.

Tests that compute_hash produces consistent 64-character hex digests
and different inputs produce different outputs.
"""
from pclipsync.hashing import compute_hash


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
