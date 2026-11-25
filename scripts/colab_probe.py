#!/usr/bin/env python
"""Probe Google Colab through the user's Brave profile with Playwright.

Copies the minimal Brave profile (cookies + prefs) to a temp folder so the
real profile stays usable while Brave is open, then opens Colab with
`authuser=4` and reports which Google account is active.

  python scripts/colab_probe.py
  python scripts/colab_probe.py --keep-open
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BRAVE = Path(r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe")
SRC = Path(os.environ["LOCALAPPDATA"]) / "BraveSoftware" / "Brave-Browser" / "User Data"
DST = Path(r"C:\Users\omega\AppData\Local\Temp\opencode\brave-colab-profile")
OUT = Path(__file__).resolve().parents[1] / "out" / "colab_probe"
COLAB_URL = "https://colab.research.google.com/?authuser=4&pli=1"

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


def copy_profile() -> None:
    if DST.exists():
        shutil.rmtree(DST, ignore_errors=True)
    (DST / "Default" / "Network").mkdir(parents=True, exist_ok=True)
    copied = 0
    for rel in FILES:
        src = SRC / rel
        if not src.exists():
            continue
        dst = DST / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    for rel in DIRS:
        src = SRC / rel
        if not src.exists():
            continue
        dst = DST / rel
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("LOCK", "LOG", "LOG.old"))
        copied += 1
    print(f"profile copied: {copied} items -> {DST}")


def dump_frames(page) -> None:
    for i, frame in enumerate(page.frames):
        try:
            text = frame.inner_text("body", timeout=3000)
        except Exception:
            continue
        text = " ".join(text.split())
        if text:
            print(f"  frame[{i}] {frame.url[:80]} :: {text[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-open", action="store_true")
    ap.add_argument("--skip-copy", action="store_true")
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    if not BRAVE.exists():
        print(f"Brave not found: {BRAVE}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    if not args.skip_copy:
        copy_profile()

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(DST),
            executable_path=str(BRAVE),
            headless=False,
            no_viewport=True,
            args=[
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-session-crashed-bubble",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(COLAB_URL, wait_until="domcontentloaded", timeout=args.timeout * 1000)
        page.wait_for_timeout(8000)

        print("title:", page.title())
        print("url:", page.url)
        page.screenshot(path=str(OUT / "01_colab.png"), full_page=False)

        html = page.content()
        print("html has team.lcsdevelopment:", "team.lcsdevelopment" in html)
        print("html has New notebook:", "New notebook" in html)

        # Account menu (iframe from accounts.google.com).
        try:
            avatar = page.locator('a[href*="SignOutOptions"], a[aria-label*="Google Account"]').first
            avatar.click(timeout=8000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "02_account_menu.png"), full_page=False)
            print("account menu frames:")
            dump_frames(page)
        except Exception as exc:
            print("account menu not opened:", exc)

        # Runtime dialog (accelerators / plan eligibility).
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            page.get_by_text("Runtime", exact=True).first.click(timeout=8000)
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "03_runtime_menu.png"), full_page=False)
            page.get_by_text("Change runtime type", exact=False).first.click(timeout=8000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "04_runtime_dialog.png"), full_page=False)
            print("runtime dialog text:")
            print(" ".join(page.inner_text("body").split())[-1200:])
        except Exception as exc:
            print("runtime dialog not opened:", exc)
            page.screenshot(path=str(OUT / "04_runtime_dialog_fail.png"), full_page=False)

        if args.keep_open:
            print("keeping browser open; press Ctrl+C to close")
            try:
                while True:
                    time.sleep(5)
            except KeyboardInterrupt:
                pass
        ctx.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
