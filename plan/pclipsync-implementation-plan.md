---
goal: Implement pclipsync - X11 clipboard synchronization over SSH-tunneled Unix domain socket
version: 1.0
date_created: 2025-12-28
last_updated: 2025-12-28
owner: pclipsync team
status: Planned
tags: [feature, implementation, clipboard, x11, ssh]
---

# Introduction

![Status: Planned](https://img.shields.io/badge/status-Planned-blue)

This plan describes the complete implementation of pclipsync, a tool that synchronizes X11 clipboards (CLIPBOARD and PRIMARY selections) between two Linux machines connected via SSH using a Unix domain socket tunneled over the SSH connection. The tool operates as a single Python script in either server mode (local machine) or client mode (remote machine).

## 1. Requirements & Constraints

- **REQ-0100**: Python 3.12 or newer required for modern type annotation syntax without typing module imports
- **REQ-0200**: Support two modes: server (local machine X) and client (remote machine Y)
- **REQ-0300**: Use Unix domain socket tunneled via SSH reverse forward (`ssh -R CLIENT_SOCKET_PATH:SERVER_SOCKET_PATH user@remote`)
- **REQ-0400**: Monitor both CLIPBOARD and PRIMARY selections; change to either updates both on remote side
- **REQ-0500**: Only support UTF8_STRING target; ignore non-text content with DEBUG-level log
- **REQ-0600**: Use netstring framing with 10 MB maximum content size
- **REQ-0700**: Implement SHA-256 hash-based loop prevention with last_sent_hash and last_received_hash
- **REQ-0800**: Server accepts exactly one client; exits with code 0 on client disconnect
- **REQ-0900**: Client retries with exponential backoff using tenacity (1s initial, 60s max, 2x multiplier, unlimited retries)
- **REQ-1000**: Graceful shutdown on SIGINT/SIGTERM with socket cleanup; no traceback on KeyboardInterrupt
- **REQ-1100**: 2-second timeout for clipboard read operations
- **REQ-1200**: Lazy imports for fast --help response; heavy imports (python-xlib) inside functions after argument validation

- **CON-100**: Individual Python files must be under 100 lines
- **CON-200**: Maximum three levels of indentation (module, function/class, one level within)
- **CON-300**: Long CLI options only; no short options
- **CON-400**: Shell wrapper uses POSIX sh (not bash) for portability
- **CON-500**: Exit codes: 0 = clean shutdown, 1 = runtime error, 2 = usage error

- **GUD-100**: Idiomatic functional style with short single-purpose functions
- **GUD-200**: Pure functions where possible for testability; IO separate from logic
- **GUD-300**: Every function must have a docstring (purpose, parameters, return value, side effects)
- **GUD-400**: Use Python 3.10+ type annotation syntax (list[str] not List[str], X | None not Optional[X])
- **GUD-500**: Use dataclasses to group related state (e.g., hash tracking state)
- **GUD-600**: Define fixed values as module-level constants with type annotations and comments
- **GUD-700**: Error messages should be informative, explaining what went wrong and suggesting fixes

- **PAT-100**: Single asyncio event loop manages both X11 and network I/O
- **PAT-200**: X11 display FD integrated into asyncio using loop.add_reader()
- **PAT-300**: Hash stored before setting clipboard to prevent echo from XFixes event
- **PAT-400**: Structure code for dependency injection where feasible

## 2. Implementation Steps

### Implementation Phase 1: Project Infrastructure

- GOAL-0100: Establish project structure, build configuration, and development tooling

> **NOTE**: Do not edit pyproject.toml by hand when a `uv` command can make the change. Use `uv add` for runtime dependencies, `uv add --dev` for development dependencies, and `uv sync` to install.

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-0100 | Create pyproject.toml with project metadata: name "pclipsync", requires-python ">=3.12", description for X11 clipboard sync over SSH | Yes | 2025-12-28 |
| TASK-0200 | Run "uv add" to add runtime dependencies: python-xlib (X11 clipboard via XFixes), click (CLI handling), tenacity (retry with exponential backoff) | Yes | 2025-12-28 |
| TASK-0300 | Run "uv add --dev" to add development dependencies: mypy (strict mode), ruff (linting/formatting), pytest, pytest-asyncio, pytest-cov, pytest-mock | Yes | 2025-12-28 |
| TASK-0400 | Create directory structure: src/pclipsync/, tests/ (bin/ already exists) | Yes | 2025-12-28 |
| TASK-0500 | Create src/pclipsync/__init__.py as empty package marker | Yes | 2025-12-28 |
| TASK-0600 | Create Makefile with default target that lists available targets using @echo for each target description | Yes | 2025-12-28 |
| TASK-0700 | Add Makefile target "ruff": runs "uv run ruff check src/" to lint source code | Yes | 2025-12-28 |
| TASK-0800 | Add Makefile target "ruff-fix": runs "uv run ruff check --fix src/" for auto-fix | Yes | 2025-12-28 |
| TASK-0900 | Add Makefile target "mypy": runs "uv run mypy src/" for type checking | Yes | 2025-12-28 |
| TASK-1000 | Add Makefile target "test": runs ruff followed by mypy (lint then type check) | Yes | 2025-12-28 |
| TASK-1100 | Run "uv sync" to create .venv/ and install dependencies | Yes | 2025-12-28 |
| TASK-1200 | Add [build-system] and [tool.hatch] sections to pyproject.toml for src/ layout so python -m pclipsync works | Yes | 2025-12-28 |

### Implementation Phase 2: Protocol Layer

- GOAL-0200: Implement netstring encoding/decoding as pure functions for clipboard content framing

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-1300 | Create src/pclipsync/protocol.py with module docstring explaining netstring framing format | Yes | 2025-12-28 |
| TASK-1400 | Define module-level constant MAX_CONTENT_SIZE: int = 10485760 (10 MB) with explanatory comment | Yes | 2025-12-28 |
| TASK-1500 | Define module-level constant MAX_LENGTH_DIGITS: int = 8 (maximum digits in length field for 10 MB max) with explanatory comment | Yes | 2025-12-28 |
| TASK-1600 | Implement function encode_netstring(data: bytes) -> bytes: takes raw clipboard bytes, returns netstring-encoded bytes in format "<length>:<content>," where length is ASCII decimal | Yes | 2025-12-28 |
| TASK-1700 | Implement function validate_content_size(data: bytes) -> bool: returns True if len(data) <= MAX_CONTENT_SIZE, False otherwise; used before encoding to check limits | Yes | 2025-12-28 |
| TASK-1800 | Create custom exception class ProtocolError(Exception) for protocol-level errors (invalid length, missing comma, size exceeded, connection closed mid-message) | Yes | 2025-12-28 |
| TASK-1900 | Implement async function read_netstring(reader: asyncio.StreamReader) -> bytes: reads length field (up to MAX_LENGTH_DIGITS ASCII digits), validates colon separator, reads content bytes, validates comma terminator, raises ProtocolError on any format violation or if length exceeds MAX_CONTENT_SIZE or connection closed mid-message (EOF) | Yes | 2025-12-28 |
| TASK-2000 | Add unit tests in tests/test_protocol.py: test encode_netstring produces correct format (e.g., b"12:Hello world!," for 12 bytes), test round-trip encode/decode, test ProtocolError raised for invalid inputs (missing colon, missing comma, length mismatch, oversized content, non-digit length field) | Yes | 2025-12-28 |

### Implementation Phase 3: Hash Utilities

- GOAL-0300: Implement SHA-256 hashing and hash state management for loop prevention

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-2100 | Create src/pclipsync/hashing.py with module docstring explaining loop prevention via hash comparison | Yes | 2025-12-28 |
| TASK-2200 | Implement function compute_hash(data: bytes) -> str: returns SHA-256 hex digest of raw clipboard bytes using hashlib.sha256 | Yes | 2025-12-28 |
| TASK-2300 | Define dataclass HashState with fields: last_sent_hash (str | None) for hash of last sent content, last_received_hash (str | None) for hash of last received content; both initialize to None | Yes | 2025-12-28 |
| TASK-2400 | Implement method HashState.should_send(current_hash: str) -> bool: returns False if current_hash equals last_sent_hash (duplicate) or last_received_hash (echo), True otherwise | Yes | 2025-12-28 |
| TASK-2500 | Implement method HashState.record_sent(hash_value: str) -> None: updates last_sent_hash after successful send (including flush) | Yes | 2025-12-28 |
| TASK-2600 | Implement method HashState.record_received(hash_value: str) -> None: updates last_received_hash; must be called BEFORE setting clipboard to prevent echo | Yes | 2025-12-28 |
| TASK-2700 | Implement method HashState.clear() -> None: resets both hashes to None; used on client reconnect for clean slate | Yes | 2025-12-28 |
| TASK-2800 | Add unit tests in tests/test_hashing.py: test compute_hash produces consistent SHA-256 hex output, test HashState.should_send returns False for duplicate/echo and True otherwise, test clear() resets state | Yes | 2025-12-28 |

### Implementation Phase 4: Clipboard Monitoring

- GOAL-0400: Implement X11 clipboard monitoring using python-xlib with XFixes extension

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-2900 | Create src/pclipsync/clipboard.py with module docstring explaining X11 clipboard monitoring via XFixes | Yes | 2025-12-28 |
| TASK-3000 | In src/pclipsync/clipboard_io.py, define module-level constant CLIPBOARD_TIMEOUT: float = 2.0 (seconds) for clipboard read timeout with explanatory comment | Yes | 2025-12-28 |
| TASK-3100 | Implement function validate_display() -> Display: checks DISPLAY environment variable is set, opens X11 connection and returns Display object, raises SystemExit with clear error message if unset or connection fails | Yes | 2025-12-28 |
| TASK-3200 | Implement function get_display_fd(display: Xlib.display.Display) -> int: returns the file descriptor for the X11 display connection for asyncio integration via loop.add_reader() | Yes | 2025-12-28 |
| TASK-3300 | Implement function create_hidden_window(display: Xlib.display.Display) -> Xlib.xobject.drawable.Window: creates a 1x1 unmapped window for owning clipboard selections when setting content from received data | Yes | 2025-12-28 |
| TASK-3400 | In src/pclipsync/clipboard_events.py, implement function register_xfixes_events(display: Xlib.display.Display, window: Window) -> None: uses XFixes extension to register for XFixesSelectionNotify events on both CLIPBOARD and PRIMARY atoms for true event-driven notification of ownership changes | Yes | 2025-12-28 |
| TASK-3500 | In src/pclipsync/clipboard_io.py, implement async function read_clipboard_content(display: Display, selection_atom: int) -> bytes | None: requests UTF8_STRING target from current clipboard owner, returns content bytes or None on failure/empty/timeout; logs non-text content at DEBUG level; uses asyncio.wait_for with CLIPBOARD_TIMEOUT | Yes | 2025-12-28 |
| TASK-3600 | In src/pclipsync/clipboard_events.py, implement function set_clipboard_content(display: Display, window: Window, content: bytes, selection_atom: int) -> bool: sets clipboard content by taking ownership of specified selection, returns True on success, False on failure; logs errors at ERROR level but does not exit | Yes | 2025-12-28 |
| TASK-3700 | In src/pclipsync/clipboard_selection.py, implement function handle_selection_request(display: Display, event: SelectionRequest, content: bytes) -> None: responds to SelectionRequest events when owning selections; supports TARGETS target (returns list: TARGETS, UTF8_STRING, STRING), UTF8_STRING (preferred, returns content as-is), STRING (legacy, returns content); refuses unsupported targets with SelectionNotify property=None | Yes | 2025-12-28 |
| TASK-3800 | In src/pclipsync/clipboard_selection.py, implement function process_pending_events(display: Display) -> list[Event]: processes only events already pending (checks pending_events() before blocking calls) to avoid stalling asyncio event loop; returns list of events (XFixesSelectionNotify and SelectionRequest) for processing | Yes | 2025-12-28 |
| TASK-3900 | Add mocked tests in tests/test_clipboard.py: mock python-xlib to test event handling logic, clipboard read/write operations, timeout handling, and error paths, SelectionRequest handling (TARGETS, UTF8_STRING, STRING targets), without requiring X11 | Yes | 2025-12-28 |

### Implementation Phase 5: Shared Sync Logic

- GOAL-0500: Implement shared synchronization logic used by both server and client

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-4000 | Create src/pclipsync/sync_state.py, sync_handlers.py, sync_loop.py, and sync.py (re-export module) with module docstring explaining bidirectional sync coordination | Yes | 2025-12-28 |
| TASK-4100 | In sync_state.py, define dataclass ClipboardState with fields: hash_state (HashState), display (Display), window (Window), current_content (bytes) for last known clipboard content | Yes | 2025-12-28 |
| TASK-4200 | In sync_handlers.py, implement async function handle_clipboard_change(state: ClipboardState, writer: StreamWriter, selection_atom: int) -> None: called when XFixesSelectionNotify received; reads clipboard content via read_clipboard_content from clipboard_io.py, computes hash via compute_hash from hashing.py, checks state.hash_state.should_send, if True encodes via encode_netstring from protocol.py and writes to socket (including flush), then calls state.hash_state.record_sent; if content exceeds 10 MB limit (checked via validate_content_size from protocol.py), logs at WARNING level "Clipboard content exceeds 10 MB limit, skipping" and skips sending; if read fails/empty/timeout, logs at DEBUG level and skips | Yes | 2025-12-28 |
| TASK-4300 | In sync_handlers.py, implement async function handle_incoming_content(state: ClipboardState, content: bytes) -> None: computes hash via compute_hash from hashing.py and calls state.hash_state.record_received BEFORE setting clipboard (critical ordering to prevent echo), then updates state.current_content and sets both CLIPBOARD and PRIMARY selections via set_clipboard_content from clipboard_events.py; if setting fails, logs at ERROR level but continues running | Yes | 2025-12-28 |
| TASK-4400 | In sync_loop.py, implement async function run_sync_loop(state: ClipboardState, reader: StreamReader, writer: StreamWriter) -> None: uses get_display_fd from clipboard.py to get X11 display FD and integrates it into asyncio using loop.add_reader(); when X11 FD is readable, calls process_pending_events from clipboard_selection.py to get pending events, then for XFixesSelectionNotify events calls handle_clipboard_change, and for SelectionRequest events using handle_selection_request from clipboard_selection.py, passing state.current_content, to serve clipboard content to other applications; concurrently reads netstrings from socket via read_netstring from protocol.py and passes decoded content to handle_incoming_content; processes clipboard events sequentially with no coalescing (hash-based dedup handles duplicates); if both CLIPBOARD and PRIMARY change simultaneously with identical content, hash deduplication ensures only one message sent | Yes | 2025-12-28 |
| TASK-4500 | Add tests in tests/test_sync.py: test handle_clipboard_change skips duplicates and echoes, test handle_incoming_content sets hash before clipboard, test oversized content logged and skipped | Yes | 2025-12-28 |

### Implementation Phase 6: Server Implementation

- GOAL-0600: Implement server mode that listens on Unix domain socket and synchronizes with single client

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-4600 | Create src/pclipsync/server.py with module docstring explaining server mode operation | Yes | 2025-12-28 |
| TASK-4700 | Implement function check_socket_state(socket_path: str) -> None: if socket file exists, attempt connection to check if active; if connection refused (stale socket), unlink and proceed; if connection succeeds (active server), raise SystemExit with error "Socket already in use by active server"; any other error, raise SystemExit with descriptive error | Yes | 2025-12-28 |
| TASK-4800 | Implement function print_startup_message(socket_path: str) -> None: prints to stderr "Listening on <socket_path>" followed by "Example SSH forward: ssh -R REMOTE_SOCKET_PATH:<socket_path> user@host" to confirm socket ready and show command template | Yes | 2025-12-28 |
| TASK-4900 | Implement function cleanup_socket(socket_path: str) -> None: that unlinks socket file; does not register handlers itself (main.py handles signal registration and calls this function) | Yes | 2025-12-28 |
| TASK-5000 | Implement async function run_server(socket_path: str) -> None: calls validate_display from clipboard.py to get X11 Display, creates hidden window via create_hidden_window from clipboard.py, registers for clipboard events via register_xfixes_events from clipboard_events.py, initializes ClipboardState with display, window, fresh HashState, and empty current_content, checks socket state via check_socket_state, creates Unix domain socket, calls print_startup_message, uses asyncio.start_unix_server to accept exactly one client connection (obtaining reader/writer pair), then runs run_sync_loop from sync.py, exits with code 0 on client disconnect; logs connection state changes at DEBUG level | Yes | 2025-12-28 |
| TASK-5100 | Add mocked tests in tests/test_server_socket.py and tests/test_server_handler.py: test socket state checking (stale vs active), test client connection handling, test proper cleanup on disconnect | Yes | 2025-12-28 |

### Implementation Phase 7: Client Implementation

- GOAL-0700: Implement client mode with exponential backoff reconnection using tenacity

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-5200 | Create client module: client.py (entry point), client_constants.py (retry params), client_retry.py (connection logic) | x | 2025-12-28 |
| TASK-5300 | Define module-level constants in client_constants.py for retry parameters with explanatory comments: INITIAL_WAIT: float = 1.0 (seconds), MAX_WAIT: float = 60.0 (seconds), WAIT_MULTIPLIER: float = 2.0 | x | 2025-12-28 |
| TASK-5400 | Implement in client_retry.py async function connect_to_server(socket_path: str) -> tuple[StreamReader, StreamWriter]: uses asyncio.open_unix_connection to open connection to Unix domain socket, returns reader/writer pair; raises ConnectionError on failure | x | 2025-12-28 |
| TASK-5500 | Implement in client_retry.py async function run_client_with_retry(socket_path: str, state: ClipboardState) -> None: wraps connection logic with tenacity retry decorator configured for: wait_exponential with initial=INITIAL_WAIT, max=MAX_WAIT, multiplier=WAIT_MULTIPLIER; retry=retry_if_exception_type for connection-related exceptions; stop=stop_never for unlimited retries; calls state.hash_state.clear() on each reconnect for clean slate, calls connect_to_server to obtain reader/writer pair, then calls run_sync_loop from sync.py for bidirectional clipboard sync; logs connection failures at WARNING level, successful connection at DEBUG level | x | 2025-12-28 |
| TASK-5600 | Implement in client.py async function run_client(socket_path: str) -> None: calls validate_display from clipboard.py to get X11 Display, creates hidden window via create_hidden_window from clipboard.py, registers for clipboard events via register_xfixes_events from clipboard_events.py, initializes ClipboardState with display, window, fresh HashState, and empty current_content, calls run_client_with_retry passing ClipboardState; this is the main client entry point | x | 2025-12-28 |
| TASK-5700 | Add mocked tests in tests/test_client_retry.py: test connection handling, test retry logic triggers on disconnect, test hash state cleared on reconnect | x | 2025-12-28 |

### Implementation Phase 8: CLI and Entry Points

- GOAL-0800: Implement command-line interface with click and shell wrapper for clean user experience

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-5800 | Create src/pclipsync/main.py with module docstring explaining CLI handling | | |
| TASK-5900 | Implement click command group with options: --server (flag, run in server mode), --client (flag, run in client mode), --socket PATH (required string, Unix domain socket path), --verbose (flag, enable DEBUG-level logging), --help (automatic from click); mutually exclusive --server and --client with error if neither or both specified | | |
| TASK-6000 | Implement function configure_logging(verbose: bool) -> None: if verbose, set logging level to DEBUG showing connection state, clipboard events, send/receive ops, skipped ops; otherwise set to WARNING (quiet default); errors always to stderr regardless of verbosity | | |
| TASK-6100 | Implement main entry point function that: validates mutually exclusive mode flags (exit code 2 on usage error), calls configure_logging, imports heavy modules (python-xlib) AFTER argument validation for fast --help, uses asyncio.run() to call run_server from server.py or run_client from client.py based on mode | | |
| TASK-6200 | Create src/pclipsync/__main__.py with minimal code: imports main from main.py and calls it; this enables python -m pclipsync invocation | | |
| TASK-6300 | Implement signal handling in main: catch SIGINT and SIGTERM, close socket connections cleanly, call cleanup_socket from server_socket.py in server mode, exit with code 0 on signal, suppress KeyboardInterrupt traceback | | |
| TASK-6400 | Create bin/pclipsync shell wrapper script using POSIX sh (not bash): resolve symlinks using realpath to find actual script location, navigate up from bin/ to project root (supports ~/bin/pclipsync -> project/bin/pclipsync symlink), check if .venv/ exists and exit with error directing user to run "uv sync" if missing, invoke .venv/bin/python -m pclipsync with all arguments passed through ("$@") | | |
| TASK-6500 | Make bin/pclipsync executable with chmod +x | | |
| TASK-6600 | Add tests in tests/test_main.py: test CLI argument validation (mutually exclusive modes, required socket), test exit codes (0 clean, 1 error, 2 usage) | | |

### Implementation Phase 9: Integration Testing

- GOAL-0900: Implement integration tests requiring X11 display (real or Xvfb)

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-6700 | Create tests/conftest.py with pytest fixtures: fixture for Xvfb display setup if available, fixture for temporary Unix domain socket path, fixture for HashState initialization | | |
| TASK-6800 | Define pytest marker "integration" in pyproject.toml for tests requiring X11 display to allow selective execution with pytest -m integration or pytest -m "not integration" | | |
| TASK-6900 | Configure pytest in pyproject.toml: add [tool.pytest.ini_options] section with markers = ["integration: marks tests as integration tests (require X11)"] to suppress unknown marker warnings | | |
| TASK-7000 | Configure pytest-asyncio in pyproject.toml: add asyncio_mode = "auto" to [tool.pytest.ini_options] section for automatic async test handling | | |
| TASK-7100 | Create tests/test_integration.py with @pytest.mark.integration: test full server-client round-trip clipboard sync (content sent from server appears on client clipboard and vice versa) | | |
| TASK-7200 | Add integration test: verify loop prevention (setting clipboard from received content does not trigger echo back to sender) | | |
| TASK-7300 | Add integration test: verify both CLIPBOARD and PRIMARY updated when either selection changes on remote | | |
| TASK-7400 | Add integration test: verify client reconnection with exponential backoff (kill server, restart, verify client reconnects and sync resumes) | | |
| TASK-7500 | Add integration test: verify graceful shutdown (send SIGTERM to server, verify socket file cleaned up and exit code 0) | | |
| TASK-7600 | Add Makefile target "test-integration": runs "uv run pytest -m integration" for integration tests only | | |
| TASK-7700 | Add Makefile target "test-unit": runs "uv run pytest -m 'not integration'" for unit tests only | | |
| TASK-7800 | Update Makefile target "test" to run ruff, mypy, then pytest (all tests) | | |

### Implementation Phase 10: Documentation and Polish

- GOAL-1000: Finalize documentation and ensure project is ready for use

| Task      | Description | Completed | Date |
| --------- | ----------- | --------- | ---- |
| TASK-7900 | Create README.md with: project description (X11 clipboard sync over SSH), installation instructions (uv sync), usage examples (server command, SSH forward command, client command), CLI reference (all options with descriptions), exit codes table, requirements (Python 3.12+, Linux, X11) | | |
| TASK-8000 | Add SSH keepalive recommendation to README.md: suggest ServerAliveInterval 30 in ssh_config or -o ServerAliveInterval=30 on command line for timely detection of connection loss | | |
| TASK-8100 | Verify all functions have docstrings explaining purpose, parameters, return value, and side effects per GUD-300 | | |
| TASK-8200 | Verify all files are under 100 lines per CON-100; split any oversized files into logical submodules | | |
| TASK-8300 | Verify no code exceeds three levels of indentation per CON-200; refactor with early returns, guard clauses, or helper functions as needed | | |
| TASK-8400 | Run full test suite (make test) and verify all tests pass | | |
| TASK-8500 | Test end-to-end workflow manually: start server, establish SSH tunnel, start client, verify clipboard sync in both directions | | |

## 3. Alternatives

- **ALT-100**: Use TCP socket instead of Unix domain socket - rejected because Unix socket provides better security (cannot be accidentally exposed to network) and simpler SSH forwarding
- **ALT-200**: Use hand-rolled retry logic instead of tenacity - rejected because tenacity is well-tested, production-proven, and handles edge cases like jitter that manual implementations often miss
- **ALT-300**: Support multiple clipboard targets (images, etc.) - deferred to future; UTF8_STRING only for initial implementation to reduce complexity
- **ALT-400**: Use threading instead of asyncio - rejected because asyncio provides cleaner integration with X11 file descriptor and avoids GIL contention issues
- **ALT-500**: Use argparse instead of click - rejected because click provides cleaner API, better error messages, and automatic --help generation

## 4. Dependencies

- **DEP-0100**: python-xlib - X11 clipboard monitoring via XFixes extension; provides Display, Window, Atom, and event handling
- **DEP-0200**: click - Command-line argument parsing with declarative syntax and automatic help generation
- **DEP-0300**: tenacity - Retry with exponential backoff; provides @retry decorator with configurable wait strategies
- **DEP-0400**: mypy - Static type checking in strict mode for catching type errors before runtime
- **DEP-0500**: ruff - Fast Python linter and formatter for consistent code style
- **DEP-0600**: pytest - Testing framework with fixtures and assertions
- **DEP-0700**: pytest-asyncio - Async test support for testing coroutines
- **DEP-0800**: pytest-cov - Test coverage reporting
- **DEP-0900**: pytest-mock - Mocking fixtures for isolating units under test
- **DEP-1000**: Standard library: asyncio, socket, hashlib, signal, logging, dataclasses (no installation needed)

## 5. Files

- **FILE-0100**: pyproject.toml - Project metadata, dependencies, build configuration
- **FILE-0200**: Makefile - Development tasks (ruff, mypy, test targets)
- **FILE-0300**: bin/pclipsync - POSIX sh wrapper script for clean user invocation
- **FILE-0400**: src/pclipsync/__init__.py - Package marker (empty)
- **FILE-0500**: src/pclipsync/__main__.py - Entry point for python -m pclipsync
- **FILE-0600**: src/pclipsync/main.py - CLI handling with click, signal handling, logging configuration
- **FILE-0700**: src/pclipsync/protocol.py - Netstring encoding/decoding, ProtocolError exception
- **FILE-0800**: src/pclipsync/hashing.py - SHA-256 hashing, HashState dataclass for loop prevention
- **FILE-0900**: src/pclipsync/clipboard.py - X11 core: display validation, window creation, display FD access
- **FILE-0950**: src/pclipsync/clipboard_io.py - X11 clipboard I/O: reading clipboard content with timeout
- **FILE-0960**: src/pclipsync/clipboard_events.py - X11 event handling: XFixes registration, set clipboard ownership
- **FILE-0970**: src/pclipsync/clipboard_selection.py - SelectionRequest handling, pending events processing
- **FILE-1000**: src/pclipsync/sync.py - Re-exports sync components from submodules
- **FILE-1010**: src/pclipsync/sync_state.py - ClipboardState dataclass
- **FILE-1020**: src/pclipsync/sync_handlers.py - handle_clipboard_change, handle_incoming_content
- **FILE-1030**: src/pclipsync/sync_loop.py - run_sync_loop, asyncio event loop integration
- **FILE-1100**: src/pclipsync/server.py - Server mode entry point (run_server)
- **FILE-1110**: src/pclipsync/server_socket.py - Socket utilities (check_socket_state, print_startup_message, cleanup_socket)
- **FILE-1120**: src/pclipsync/server_handler.py - Client connection handler (handle_client)
- **FILE-1200**: src/pclipsync/client.py - Client mode entry point (run_client)
- **FILE-1210**: src/pclipsync/client_constants.py - Retry configuration constants
- **FILE-1220**: src/pclipsync/client_retry.py - Connection and tenacity retry logic
- **FILE-1300**: tests/conftest.py - Pytest fixtures and configuration
- **FILE-1400**: tests/test_protocol.py - Unit tests for netstring encoding/decoding
- **FILE-1500**: tests/test_hashing.py - Unit tests for hash computation and HashState
- **FILE-1600**: tests/test_clipboard.py - Mocked tests for clipboard and clipboard_io operations
- **FILE-1700**: tests/test_sync.py - Tests for sync logic
- **FILE-1800**: tests/test_server_socket.py - Tests for server socket utilities
- **FILE-1810**: tests/test_server_handler.py - Tests for server client handler
- **FILE-1900**: tests/test_client_retry.py - Mocked tests for client connection and retry
- **FILE-2000**: tests/test_main.py - Tests for CLI argument handling
- **FILE-2100**: tests/test_integration.py - Integration tests requiring X11
- **FILE-2200**: README.md - User documentation

## 6. Testing

- **TEST-0100**: Unit test protocol.encode_netstring produces correct format (length:content,)
- **TEST-0200**: Unit test protocol.read_netstring correctly decodes valid netstrings
- **TEST-0300**: Unit test protocol.read_netstring raises ProtocolError for invalid inputs (missing colon, missing comma, length mismatch, oversized, non-digit length, length field exceeding 8 digits)
- **TEST-0400**: Unit test round-trip: read_netstring(encode_netstring(data)) == data
- **TEST-0500**: Unit test hashing.compute_hash produces consistent SHA-256 hex output
- **TEST-0600**: Unit test HashState.should_send returns False for duplicate (matches last_sent_hash)
- **TEST-0700**: Unit test HashState.should_send returns False for echo (matches last_received_hash)
- **TEST-0800**: Unit test HashState.should_send returns True for new content
- **TEST-0900**: Unit test HashState.clear resets both hashes to None
- **TEST-1000**: Mocked test clipboard read with timeout
- **TEST-1100**: Mocked test non-text clipboard content (images, etc.) is ignored with DEBUG-level log and read returns None
- **TEST-1200**: Mocked test empty clipboard read logs at DEBUG level and skips sending (no message sent)
- **TEST-1300**: Mocked test clipboard set success and failure paths
- **TEST-1400**: Mocked test XFixes event handling
- **TEST-1500**: Mocked test SelectionRequest handling: TARGETS returns available targets list, UTF8_STRING returns content, STRING returns content for legacy apps, unsupported targets refused with property=None
- **TEST-1600**: Test sync.handle_clipboard_change skips when should_send returns False
- **TEST-1700**: Test sync.handle_incoming_content calls record_received before set_clipboard
- **TEST-1800**: Test sync.handle_clipboard_change logs WARNING and skips for oversized content
- **TEST-1900**: Test server socket state checking (stale vs active)
- **TEST-2000**: Test server prints startup message to stderr with socket path and SSH forward example
- **TEST-2100**: Test client retry logic invokes tenacity on disconnect
- **TEST-2200**: Test client clears hash state on reconnect
- **TEST-2300**: Test CLI mutual exclusion of --server and --client
- **TEST-2400**: Test CLI exit code 2 on usage error
- **TEST-2500**: Test CLI exit code 1 on runtime error (e.g., X11 connection failure, socket error)
- **TEST-2600**: Integration test full round-trip sync
- **TEST-2700**: Integration test loop prevention
- **TEST-2800**: Integration test CLIPBOARD and PRIMARY both updated
- **TEST-2900**: Integration test client reconnection
- **TEST-3000**: Integration test graceful shutdown with socket cleanup

## 7. Risks & Assumptions

- **RISK-100**: python-xlib may have undocumented behavior with XFixes extension; mitigation: test thoroughly with real X11 displays
- **RISK-200**: SSH connection drops may not be detected quickly without keepalive; mitigation: document SSH keepalive configuration
- **RISK-300**: Clipboard owner may be unresponsive causing hangs; mitigation: 2-second timeout on all clipboard reads
- **RISK-400**: Large clipboard content may cause memory pressure; mitigation: 10 MB limit enforced at protocol level

- **ASSUMPTION-100**: SSH reverse tunnel is established before client starts (user responsibility)
- **ASSUMPTION-200**: Both machines have X11 displays available (DISPLAY environment variable set)
- **ASSUMPTION-300**: User has appropriate permissions for Unix domain socket paths
- **ASSUMPTION-400**: python-xlib correctly implements XFixes extension for selection monitoring
- **ASSUMPTION-500**: SelectionClear events do not require explicit handling because XFixes' XFixesSelectionNotify already notifies about ownership changes; when we lose ownership, no cleanup is needed and XFixes tells us about the new owner

## 8. Related Specifications / Further Reading

- [pclipsync-architecture.md](../architecture/pclipsync-architecture.md) - Original architecture specification
- [python-xlib documentation](https://python-xlib.github.io/) - X11 Python bindings
- [XFixes Extension](https://www.x.org/releases/current/doc/fixesproto/fixesproto.txt) - X11 selection monitoring protocol
- [Netstring specification](https://cr.yp.to/proto/netstrings.txt) - D. J. Bernstein's netstring format
- [tenacity documentation](https://tenacity.readthedocs.io/) - Retry library for Python
- [click documentation](https://click.palletsprojects.com/) - CLI framework for Python
