#!/usr/bin/env python
"""Walk the Colab CLI OAuth consent in the running Brave (CDP) and print the code.

Usage:
  python scripts/colab_oauth_browser.py --auth-url "<url>"

Reads the URL from --auth-url or from /tmp/colab_auth.log (WSL path
\\\\wsl.localhost\\... is not used; pass the URL explicitly).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "out" / "colab_oauth"

CODE_RE = re.compile(r"\b(4/[0-9A-Za-z_\-\.]{20,})")
FALLBACK_RE = re.compile(r"\b([0-9]/[0-9A-Za-z_\-\.]{20,})")


def text_of(page) -> str:
    try:
        return " ".join(page.inner_text("body", timeout=5000).split())
    except Exception:
        return ""


def dump(page, tag: str) -> str:
    t = text_of(page)
    print(f"[{tag}] url={page.url[:110]}")
    print(f"[{tag}] text={t[:700]}")
    page.screenshot(path=str(OUT / f"{tag}.png"), full_page=False)
    return t


def click_any(page, labels: list[str], timeout: int = 4000) -> bool:
    for label in labels:
        try:
            loc = page.get_by_role("button", name=re.compile(label, re.I))
            if loc.count():
                loc.first.click(timeout=timeout)
                return True
        except Exception:
            pass
        try:
            loc = page.get_by_text(re.compile(rf"^{label}$", re.I))
            if loc.count():
                loc.first.click(timeout=timeout)
                return True
        except Exception:
            pass
    return False


def find_code(text: str) -> str | None:
    for rx in (CODE_RE, FALLBACK_RE):
        m = rx.search(text)
        if m:
            return m.group(1)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-url", required=True)
    ap.add_argument("--account", default="team.lcsdevelopment")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    url = args.auth_url
    if "authuser=" not in url:
        url += "&authuser=4"

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)
        dump(page, "01_landing")

        for step in range(1, 9):
            text = text_of(page)
            code = find_code(text)
            if code:
                print(f"CODE:{code}")
                dump(page, f"{step:02d}_code")
                return 0

            # Account chooser
            if "choose an account" in text.lower() or "pilih akun" in text.lower():
                try:
                    page.get_by_text(re.compile(args.account, re.I)).first.click(timeout=5000)
                    page.wait_for_timeout(3500)
                    dump(page, f"{step:02d}_account")
                    continue
                except Exception as exc:
                    print("account click failed:", exc)

            clicked = click_any(
                page,
                [
                    "Continue",
                    "Allow",
                    "Next",
                    "Lanjutkan",
                    "Izinkan",
                    "Setujui",
                    "Confirm",
                    "Sign in",
                    "Masuk",
                ],
            )
            if clicked:
                page.wait_for_timeout(3500)
                dump(page, f"{step:02d}_clicked")
                continue

            # Try any checkbox (consent often needs it) then retry click.
            try:
                boxes = page.locator('input[type="checkbox"]:not(:checked)')
                if boxes.count():
                    boxes.first.check(timeout=3000)
                    print("checked a consent checkbox")
                    page.wait_for_timeout(800)
                    continue
            except Exception:
                pass

            print("no action found at step", step)
            break

        text = text_of(page)
        code = find_code(text)
        if code:
            print(f"CODE:{code}")
            return 0
        print("NO_CODE_FOUND")
        dump(page, "99_final")
    return 1


if __name__ == "__main__":
    sys.exit(main())
