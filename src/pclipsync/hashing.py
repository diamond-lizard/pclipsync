#!/usr/bin/env python3
"""
SHA-256 hashing and hash state management for loop prevention.

Loop prevention is critical for clipboard synchronization to avoid infinite
echo loops. When clipboard content is set from received data, the XFixes
extension generates a selection change event. Without tracking, this would
trigger sending the same content back, creating an endless loop.

This module provides:
- compute_hash(): SHA-256 hex digest of clipboard content
- HashState: dataclass tracking last_sent_hash and last_received_hash

The hash state tracks two values:
- last_sent_hash: Prevents duplicate sends of unchanged content
- last_received_hash: Prevents echo (sending back what we just received)

Critical ordering: record_received() must be called BEFORE setting the
clipboard to ensure the resulting XFixes event is recognized as an echo.
"""
import hashlib
from pclipsync.hash_state import HashState

__all__ = ["compute_hash", "HashState"]


def compute_hash(data: bytes) -> str:
    """
    Compute SHA-256 hash of clipboard content.

    Args:
        data: Raw clipboard content bytes to hash.

    Returns:
        Hexadecimal string representation of the SHA-256 digest.
    """
    return hashlib.sha256(data).hexdigest()


