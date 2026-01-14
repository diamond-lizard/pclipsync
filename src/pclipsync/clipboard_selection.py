"""X11 selection request handling - compatibility re-exports.

This module re-exports all public symbols from the refactored submodules
for backward compatibility. New code should import directly from the
specific submodules.
"""

# Re-export constants and IncrSendState
from pclipsync.clipboard_selection_incr_state import (
    INCR_SAFETY_MARGIN,
    INCR_CHUNK_SIZE,
    INCR_SEND_TIMEOUT,
    IncrSendState,
)

# Re-export threshold detection
from pclipsync.clipboard_selection_incr_needs import (
    get_max_property_size,
    needs_incr_transfer,
)

# Re-export subscription management
from pclipsync.clipboard_selection_incr_subscribe import (
    unsubscribe_requestor_events,
    unsubscribe_incr_requestor,
)

# Re-export INCR initiation
from pclipsync.clipboard_selection_incr_initiate import initiate_incr_send

# Re-export INCR chunk sending
from pclipsync.clipboard_selection_incr_chunk import send_incr_chunk

# Re-export INCR event detection
from pclipsync.clipboard_selection_incr_events import is_incr_send_event

# Re-export INCR event handling
from pclipsync.clipboard_selection_incr_handle import handle_incr_send_event

# Re-export INCR cleanup
from pclipsync.clipboard_selection_incr_cleanup import (
    cleanup_stale_incr_sends,
    cleanup_incr_sends_on_ownership_loss,
)

# Re-export selection request handling
from pclipsync.clipboard_selection_request import handle_selection_request

# Re-export event processing
from pclipsync.clipboard_selection_process import process_pending_events

__all__ = [
    "INCR_SAFETY_MARGIN",
    "INCR_CHUNK_SIZE",
    "INCR_SEND_TIMEOUT",
    "IncrSendState",
    "get_max_property_size",
    "needs_incr_transfer",
    "unsubscribe_requestor_events",
    "unsubscribe_incr_requestor",
    "initiate_incr_send",
    "send_incr_chunk",
    "is_incr_send_event",
    "handle_incr_send_event",
    "cleanup_stale_incr_sends",
    "cleanup_incr_sends_on_ownership_loss",
    "handle_selection_request",
    "process_pending_events",
]
