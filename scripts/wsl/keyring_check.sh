#!/usr/bin/env bash
# Inspect the keyring backend used by the Colab CLI inside WSL.
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
T=/home/omega/.local/share/uv/tools/google-colab-cli

echo "DBUS_SESSION_BUS_ADDRESS=${DBUS_SESSION_BUS_ADDRESS:-<empty>}"
"$T/bin/python" - <<'PY'
import keyring
try:
    from keyring.backends import fail
except Exception:
    fail = None
kr = keyring.get_keyring()
print("backend:", type(kr).__module__ + "." + type(kr).__name__)
print("priority:", getattr(kr, "priority", None))
print("is_fail:", kr is getattr(fail, "Keyring", None))
PY

echo "--- configured backends ---"
"$T/bin/python" -c "import keyring.core; print(keyring.core.get_all_keyring())" 2>&1 | tail -3

echo "--- token file ---"
ls -la "$HOME/.config/colab-cli/" 2>&1
