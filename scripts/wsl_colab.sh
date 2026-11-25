#!/usr/bin/env bash
# Wrapper so `colab` works from Windows PowerShell via WSL without the
# corrupted WSL PATH (Windows PATH is injected unquoted, breaking bash).
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
exec colab "$@"
