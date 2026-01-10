#!/usr/bin/env python3
"""
Hash state management for loop prevention.

Loop prevention is critical for clipboard synchronization to avoid infinite
echo loops. When clipboard content is set from received data, the XFixes
extension generates a selection change event. Without tracking, this would
trigger sending the same content back, creating an endless loop.

The hash state tracks two values:
- last_sent_hash: Prevents duplicate sends of unchanged content
- last_received_hash: Prevents echo (sending back what we just received)

Critical ordering: record_received() must be called BEFORE setting the
clipboard to ensure the resulting XFixes event is recognized as an echo.
"""
from dataclasses import dataclass


@dataclass
class HashState:
    """
    Track hashes for loop prevention.

    Maintains the hash of the last sent and last received clipboard content
    to prevent duplicate sends and echo loops.

    Attributes:
        last_sent_hash: SHA-256 hex digest of last sent content, or None.
        last_received_hash: SHA-256 hex digest of last received content, or None.
    """

    last_sent_hash: str | None = None
    last_received_hash: str | None = None

    def should_send(self, current_hash: str) -> bool:
        """
        Check if content should be sent based on hash comparison.

        Returns False if current_hash matches last_sent_hash (duplicate send)
        or last_received_hash (echo of received content). Returns True otherwise.

        Args:
            current_hash: SHA-256 hex digest of current clipboard content.

        Returns:
            True if content should be sent, False if duplicate or echo.
        """
        if current_hash == self.last_sent_hash:
            return False
        if current_hash == self.last_received_hash:
            return False
        return True

    def record_sent(self, hash_value: str) -> None:
        """
        Record hash of successfully sent content.

        Call this after successful send (including flush) to prevent
        duplicate sends of the same content.

        Args:
            hash_value: SHA-256 hex digest of sent content.
        """
        self.last_sent_hash = hash_value

    def record_received(self, hash_value: str) -> None:
        """
        Record hash of received content.

        CRITICAL: Must be called BEFORE setting clipboard to prevent the
        resulting XFixes event from triggering an echo send.

        Args:
            hash_value: SHA-256 hex digest of received content.
        """
        self.last_received_hash = hash_value


    def clear_received_hash(self) -> None:
        """
        Clear the last received hash to allow sending matching content.

        The received hash prevents "echo" where content we just received
        bounces back. However, this protection should only apply briefly
        after receiving. Once another application takes clipboard ownership,
        any content we subsequently read comes from that application, not
        from echo of our received content.

        Call this when we lose clipboard ownership to another application.
        """
        self.last_received_hash = None

    def clear_sent_hash(self) -> None:
        """
        Clear the last sent hash to allow sending matching content.

        The sent hash prevents "duplicate" sends of unchanged content.
        However, this protection should only apply while we own the clipboard.
        Once another application takes clipboard ownership, any content we
        subsequently read comes from that application and should be sent,
        even if it happens to match something we previously sent.

        Call this when we lose clipboard ownership to another application.
        """
        self.last_sent_hash = None

    def clear(self) -> None:
        """
        Reset hash state to initial values.

        Used on client reconnect to ensure a clean slate where the first
        clipboard content will be sent regardless of what was sent before.
        """
        self.last_sent_hash = None
        self.last_received_hash = None
