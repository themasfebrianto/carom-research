#!/usr/bin/env bash
# Feed the authorization code to the waiting Colab CLI and print the result.
set -u
LOG=/tmp/colab_auth.log
FIFO=/tmp/colab_code.fifo

CODE="${1:-}"
if [ -z "$CODE" ]; then
  echo "usage: colab_auth_code.sh <code>" >&2
  exit 2
fi

if [ ! -p "$FIFO" ]; then
  echo "no FIFO at $FIFO; run colab_auth_start.sh first" >&2
  exit 1
fi

printf '%s\n' "$CODE" > "$FIFO"
echo "code submitted, waiting..."
sleep 12
echo "--- log ---"
cat "$LOG" 2>/dev/null
