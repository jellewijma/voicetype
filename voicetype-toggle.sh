#!/bin/bash
# VoiceType toggle wrapper - starts VoiceType if not running, then toggles recording

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOCKET="/tmp/voicetype.sock"
PYTHON="$SCRIPT_DIR/venv/bin/python"
SCRIPT="$SCRIPT_DIR/src/voicetype.py"

# Send toggle command via socket
send_toggle() {
    echo "toggle" | nc -U "$SOCKET" 2>/dev/null
}

# Check if socket exists and is actually alive (not stale)
is_socket_alive() {
    python3 -c "import socket; s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.connect('$SOCKET'); s.close()" 2>/dev/null
}

# If socket exists and is alive, send toggle command
if [ -S "$SOCKET" ] && is_socket_alive; then
    send_toggle
    exit 0
fi

# Start VoiceType in background with auto-record flag
if [ -x "$PYTHON" ] && [ -f "$SCRIPT" ]; then
    "$PYTHON" "$SCRIPT" --auto-record &
    # Wait for socket to appear (max 5 seconds)
    for i in {1..50}; do
        [ -S "$SOCKET" ] && break
        sleep 0.1
    done
    # Send toggle command (auto-record will start recording automatically,
    # but sending toggle ensures recording starts even if auto-record fails)
    send_toggle
else
    echo "Error: VoiceType not found at $SCRIPT" >&2
    exit 1
fi