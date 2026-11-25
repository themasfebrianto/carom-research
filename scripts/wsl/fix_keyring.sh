#!/usr/bin/env bash
# Give the Colab CLI a working keyring in WSL (no Secret Service available).
# Uses keyrings.alt PlaintextKeyring stored in ~/.local/share/python_keyring.
set -eu
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
T=/home/omega/.local/share/uv/tools/google-colab-cli

uv pip install --python "$T/bin/python" keyrings.alt 2>&1 | tail -3

mkdir -p "$HOME/.config/python_keyring"
cat > "$HOME/.config/python_keyring/keyringrc.cfg" <<'CFG'
[backend]
default-keyring = keyrings.alt.file.PlaintextKeyring
CFG
chmod 700 "$HOME/.config/python_keyring"
chmod 600 "$HOME/.config/python_keyring/keyringrc.cfg"

"$T/bin/python" - <<'PY'
import keyring
kr = keyring.get_keyring()
print("backend:", type(kr).__module__ + "." + type(kr).__name__)
keyring.set_password("colab-cli-selftest", "u", "v")
print("roundtrip:", keyring.get_password("colab-cli-selftest", "u"))
keyring.delete_password("colab-cli-selftest", "u")
PY
