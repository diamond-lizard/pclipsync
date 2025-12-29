#!/usr/bin/env python3
"""Constants for client mode retry configuration.

These constants control the exponential backoff behavior for client
reconnection when the connection to the server is lost.
"""

# Retry parameters for exponential backoff reconnection.
# Initial delay between connection attempts in seconds.
INITIAL_WAIT: float = 1.0

# Maximum delay between connection attempts in seconds.
MAX_WAIT: float = 60.0

# Multiplier for exponential backoff (delay = initial * multiplier^attempt).
WAIT_MULTIPLIER: float = 2.0
