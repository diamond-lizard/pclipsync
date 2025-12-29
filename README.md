# pclipsync

X11 clipboard synchronization between two Linux machines over an SSH-tunneled Unix domain socket.

## Overview

pclipsync synchronizes the CLIPBOARD and PRIMARY selections between a local workstation and a remote server connected via SSH. Changes to either selection on one machine are automatically replicated to both selections on the other machine.

## Requirements

- Python 3.12 or newer
- Linux with X11 (both machines)
- SSH access to the remote machine

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd pclipsync

# Install dependencies
uv sync

# The bin/pclipsync wrapper is now ready to use
```

### Standalone Binary

To create a standalone executable that can be copied to remote machines without
requiring uv or installing dependencies:

```bash
make shiv
```

This produces `pclipsync.pyz`, a self-contained zipapp that only requires
Python 3.12+ to run. Copy it to the remote machine and run directly:

```bash
./bin/pclipsync.pyz --client --socket /path/to/socket
```

## Usage

### 1. Start the server on your local machine

```bash
./bin/pclipsync --server --socket /tmp/pclipsync.sock
```

The server will print a message confirming the socket is ready and show an example SSH command.

### 2. Establish the SSH tunnel with socket forwarding

```bash
ssh -o StreamLocalBindUnlink=yes -R /tmp/pclipsync-remote.sock:/tmp/pclipsync.sock user@remote-host
```

This creates a reverse tunnel that forwards the remote socket to your local server.

### 3. Start the client on the remote machine

```bash
./bin/pclipsync --client --socket /tmp/pclipsync-remote.sock
```

The client connects to the server through the SSH-tunneled socket. Clipboard changes now sync bidirectionally.

## CLI Reference

```
pclipsync --server --socket PATH [--verbose] [--help]
pclipsync --client --socket PATH [--verbose] [--help]
```

| Option      | Description                              |
|-------------|------------------------------------------|
| --server    | Run in server mode (local machine)       |
| --client    | Run in client mode (remote machine)      |
| --socket    | Path to Unix domain socket (required)    |
| --verbose   | Enable DEBUG-level logging               |
| --help      | Show help message                        |

Note: --server and --client are mutually exclusive; exactly one must be specified.

## Exit Codes

| Code | Meaning                                   |
|------|-------------------------------------------|
| 0    | Clean shutdown (signal or client disconnect in server mode) |
| 1    | Runtime error                             |
| 2    | Usage error (invalid arguments)           |

## SSH Keepalive Configuration

For timely detection of connection loss, configure SSH keepalive settings:

```bash
# On command line
ssh -o StreamLocalBindUnlink=yes -o ServerAliveInterval=30 -R /tmp/pclipsync-remote.sock:/tmp/pclipsync.sock user@host

# Or in ~/.ssh/config
Host remote-host
    ServerAliveInterval 30
```

This sends a keepalive packet every 30 seconds. If the connection drops, SSH will detect it and terminate, allowing pclipsync to handle the disconnection appropriately.

## Stale Socket Cleanup

When SSH creates a reverse tunnel with `-R`, the sshd daemon creates a Unix socket file on
the remote machine. If the SSH connection terminates uncleanly (network failure, killed
process, etc.), this socket file may be left behind as a "stale" socket.

When you establish a new SSH tunnel, sshd may fail to bind to the socket path because the
stale file still exists, and the pclipsync client will be unable to connect.

**Symptoms of stale socket problems:**

- pclipsync client exits with "Connection failed" error
- The SSH tunnel appears to connect successfully
- Manually removing the remote socket file fixes the issue

**Recommended fix (requires root on remote machine):**

Add `StreamLocalBindUnlink yes` to `/etc/ssh/sshd_config` on the remote machine and restart
sshd. This tells sshd to automatically remove any existing socket file before creating a new
one, ensuring reliable reconnection even after unclean disconnections.

```
# Add to /etc/ssh/sshd_config on remote machine:
StreamLocalBindUnlink yes
```

Then restart sshd (e.g., `sudo systemctl restart sshd`).

**Note:** The `-o StreamLocalBindUnlink=yes` option shown in the SSH examples only affects
sockets created by the ssh client locally (for `-L` forwards). For `-R` forwards, the socket
is created by sshd on the remote machine, so the sshd configuration is required.

**Manual workaround (if you cannot modify sshd config):**

Remove the stale socket file on the remote machine before re-establishing the SSH tunnel:

```bash
ssh user@remote-host "rm -f /path/to/remote/socket"
```

## How It Works

1. Both server and client monitor X11 clipboard changes using the XFixes extension
2. When a clipboard change is detected, the content is hashed (SHA-256) and compared against previously sent/received hashes to prevent loops
3. New content is encoded using netstring framing and sent over the Unix socket
4. The receiver updates both CLIPBOARD and PRIMARY selections with the new content
5. Only UTF8_STRING (text) content is synchronized; non-text content is ignored

## Limitations

- Text only: Images and other non-text clipboard content are not synchronized
- Maximum content size: 10 MB per clipboard transfer
- Single client: The server accepts exactly one client connection

## License

See LICENSE file for details.
