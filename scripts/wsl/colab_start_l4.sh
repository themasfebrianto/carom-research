#!/usr/bin/env bash
# Provision an L4 session, report GPU identity + live burn rate.
set -u
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
S=centerloc

echo "=== new session ==="
colab new --gpu L4 --session "$S" 2>&1 | tail -20

echo "=== status ==="
colab status -s "$S" 2>&1 | tail -20

echo "=== gpu probe ==="
cat > /tmp/probe.py <<'PY'
import subprocess, torch
print("torch:", torch.__version__)
print("cuda:", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print("gpu:", p.name, round(p.total_memory / 1024**3, 1), "GiB", "sm", p.major, p.minor)
print(subprocess.run(
    ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
    capture_output=True, text=True).stdout.strip())
import os
print("cpu:", os.cpu_count(), "ram_gib:", round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1))
PY
colab exec -s "$S" -f /tmp/probe.py --timeout 240 2>&1 | tail -25

echo "=== usage ==="
colab usage 2>&1 | tail -10
