#!/usr/bin/env python
"""Copy the minimal Brave profile for Playwright, even while Brave is running.

Chromium keeps `Default/Network/Cookies` open with an exclusive Windows share
mode, so a plain copy fails.  When the shell is elevated we take a Volume
Shadow Copy and read the files from the snapshot instead; otherwise the script
asks you to close Brave first.

  python scripts/copy_brave_profile.py
  python scripts/copy_brave_profile.py --out C:\\temp\\brave-profile
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SRC = Path(os.environ["LOCALAPPDATA"]) / "BraveSoftware" / "Brave-Browser" / "User Data"
DEFAULT_OUT = Path(r"C:\Users\omega\AppData\Local\Temp\opencode\brave-colab-profile")

FILES = [
    "Local State",
    "Default/Preferences",
    "Default/Secure Preferences",
    "Default/Network/Cookies",
    "Default/Network/Cookies-journal",
    "Default/Network/Cookies-wal",
    "Default/Network/Cookies-shm",
    "Default/Login Data",
]
DIRS = [
    "Default/Local Storage",
    "Default/Session Storage",
]


def make_shadow() -> tuple[str, str] | None:
    ps = r"""
$class = [wmiclass]'Win32_ShadowCopy'
$res = $class.Create('C:\', 'ClientAccessible')
if ($res.ReturnValue -ne 0) { Write-Output "ERR:$($res.ReturnValue)"; exit 1 }
$sc = Get-WmiObject Win32_ShadowCopy | Where-Object { $_.ID -eq $res.ShadowID }
Write-Output "DEV:$($sc.DeviceObject)"
Write-Output "ID:$($res.ShadowID)"
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=120,
    )
    dev = sid = ""
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("DEV:"):
            dev = line[4:]
        elif line.startswith("ID:"):
            sid = line[3:]
    if not dev or not sid:
        print(proc.stdout)
        print(proc.stderr)
        return None
    return dev, sid


def delete_shadow(sid: str) -> None:
    ps = (
        "$s = Get-WmiObject Win32_ShadowCopy | Where-Object { $_.ID -eq '"
        + sid
        + "' }; if ($s) { $s.Delete() | Out-Null; Write-Output 'deleted' }"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True, text=True, timeout=60,
    )


def copy_tree(src_root: Path, out: Path) -> None:
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    (out / "Default" / "Network").mkdir(parents=True, exist_ok=True)
    n = 0
    for rel in FILES:
        src = src_root / rel
        if not src.exists():
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        n += 1
    for rel in DIRS:
        src = src_root / rel
        if not src.exists():
            continue
        shutil.copytree(
            src, out / rel, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("LOCK", "LOG", "LOG.old"),
        )
        n += 1
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"copied {n} items, {total/1024/1024:.1f} MB -> {out}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-vss", action="store_true")
    args = ap.parse_args()
    src = Path(args.src)
    out = Path(args.out)

    try:
        copy_tree(src, out)
        return 0
    except PermissionError as exc:
        print(f"direct copy blocked: {exc}")

    if args.no_vss:
        print("close Brave and retry, or run without --no-vss as administrator")
        return 1

    shadow = make_shadow()
    if not shadow:
        print("could not create a shadow copy")
        return 1
    dev, sid = shadow
    try:
        # C:\Users\<user>\... -> snapshot path
        rel = Path(src).relative_to("C:\\")
        snap_src = Path(dev) / rel
        print(f"reading from shadow: {snap_src}")
        copy_tree(snap_src, out)
    finally:
        delete_shadow(sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
