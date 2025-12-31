#!/usr/bin/env python3
"""
Netstring framing for clipboard content.

Netstrings provide a simple, reliable framing format for transmitting
arbitrary binary data over a stream connection. Format: <length>:<content>,
where length is ASCII decimal digits, followed by a colon, the raw content
bytes, and a trailing comma.

Example: "12:Hello world!," encodes the 12-byte string "Hello world!".

This module provides encoding and decoding functions for netstrings,
with a maximum content size of 10 MB to prevent memory exhaustion.
"""
import asyncio

# Maximum size of clipboard content in bytes (10 MB).
# Prevents memory exhaustion from extremely large clipboard data.
MAX_CONTENT_SIZE: int = 10485760

# Maximum digits in the length field (8 digits allows up to 99999999 bytes).
# Enforced during parsing to prevent denial of service from huge length values.
MAX_LENGTH_DIGITS: int = 8

# Goodbye message: empty netstring signaling clean shutdown.
# Sent before intentional disconnect (SIGINT/SIGTERM).
GOODBYE_MESSAGE: bytes = b"0:,"


def encode_netstring(data: bytes) -> bytes:
    """
    Encode raw bytes as a netstring.

    Args:
        data: Raw clipboard content bytes to encode.

    Returns:
        Netstring-encoded bytes in format "<length>:<content>,".
    """
    length = len(data)
    return f"{length}:".encode("ascii") + data + b","


def validate_content_size(data: bytes) -> bool:
    """
    Check if content size is within the allowed limit.

    Args:
        data: Raw clipboard content bytes to validate.

    Returns:
        True if len(data) <= MAX_CONTENT_SIZE, False otherwise.
    """
    return len(data) <= MAX_CONTENT_SIZE


class ProtocolError(Exception):
    """
    Exception raised for protocol-level errors.

    Raised when netstring parsing fails due to invalid format, size
    violations, or connection issues during message reading.
    """

    pass


async def read_netstring(reader: asyncio.StreamReader) -> bytes:
    """
    Read and decode a netstring from an async stream.

    Args:
        reader: asyncio StreamReader to read from.

    Returns:
        Decoded content bytes.

    Raises:
        ProtocolError: On invalid format, size violation, or connection closed.
    """
    length_bytes = b""
    while len(length_bytes) < MAX_LENGTH_DIGITS + 1:
        byte = await reader.read(1)
        if not byte:
            raise ProtocolError("Connection closed while reading length field")
        if byte == b":":
            break
        if not byte.isdigit():
            raise ProtocolError(f"Invalid character in length field: {byte!r}")
        length_bytes += byte
    else:
        raise ProtocolError("Length field exceeds maximum digits")
    if not length_bytes:
        raise ProtocolError("Empty length field")
    length = int(length_bytes.decode("ascii"))
    if length > MAX_CONTENT_SIZE:
        raise ProtocolError(f"Content size {length} exceeds limit {MAX_CONTENT_SIZE}")
    try:
        content = await reader.readexactly(length)
    except asyncio.IncompleteReadError as e:
        raise ProtocolError(f"Connection closed after {e.partial!r} bytes") from e
    comma = await reader.read(1)
    if comma != b",":
        raise ProtocolError(f"Expected comma terminator, got {comma!r}")
    return content


# Timeout for goodbye message drain in seconds.
# Short timeout since we're shutting down and connection may be dead.
GOODBYE_DRAIN_TIMEOUT: float = 2.0


async def send_goodbye(writer: asyncio.StreamWriter) -> None:
    """
    Send goodbye message to signal clean shutdown.
    
    Sends the empty netstring (0:,) which signals intentional disconnect.
    Errors are silently ignored since the connection may already be dead
    during shutdown.
    
    Args:
        writer: asyncio StreamWriter to send goodbye on.
    """
    try:
        writer.write(b"0:,")
        await asyncio.wait_for(writer.drain(), timeout=GOODBYE_DRAIN_TIMEOUT)
    except (OSError, asyncio.TimeoutError):
        pass


def is_goodbye(content: bytes) -> bool:
    """
    Check if content is a goodbye message (empty bytes).
    
    The goodbye message is an empty netstring (0:,), which decodes to
    empty bytes. This signals intentional clean shutdown.
    
    Args:
        content: Decoded netstring content to check.
    
    Returns:
        True if content is empty bytes, False otherwise.
    """
    return content == b""
