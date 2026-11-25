#!/usr/bin/env bash
# Start the Colab CLI OAuth flow in the background and print the auth URL.
# The CLI waits for the authorization code on a FIFO so we can feed it later
# (see colab_auth_code.sh) after opening the URL in the real Brave session.
set -eu
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
LOG=/tmp/colab_auth.log
FIFO=/tmp/colab_code.fifo

rm -f "$LOG" "$FIFO"
mkfifo "$FIFO"

# Hold the write end open so the CLI does not read EOF and abort.
( sleep 1800 ) > "$FIFO" &
HOLDER=$!
echo "holder pid: $HOLDER"

setsid nohup bash -c "colab usage < '$FIFO' > '$LOG' 2>&1" >/dev/null 2>&1 &
sleep 8

echo "--- log ---"
cat "$LOG" 2>/dev/null || echo "(no log yet)"
