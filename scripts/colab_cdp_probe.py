#!/usr/bin/env python
"""Check the Colab session in the already-running Brave (CDP port 9222).

Brave must have been started with --remote-debugging-port=9222.  This script
does not close the browser; it only opens a tab and reports the account.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "out" / "colab_probe"
URL = "https://colab.research.google.com/?authuser=4&pli=1"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        print("pages:", [pg.url[:90] for pg in ctx.pages])
        page = ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(9000)
        print("title:", page.title())
        print("url:", page.url)
        page.screenshot(path=str(OUT / "cdp_01_colab.png"), full_page=False)
        html = page.content()
        print("has team.lcsdevelopment:", "team.lcsdevelopment" in html)
        print("has Sign in:", "Sign in" in html)
        print("has New notebook:", "New notebook" in html)

        # account menu
        try:
            avatar = page.locator('a[href*="SignOutOptions"], a[aria-label*="Google Account"]').first
            avatar.click(timeout=8000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "cdp_02_account.png"), full_page=False)
            for i, frame in enumerate(page.frames):
                try:
                    text = " ".join(frame.inner_text("body", timeout=2000).split())
                except Exception:
                    continue
                if text:
                    print(f"frame[{i}] {frame.url[:70]} :: {text[:260]}")
        except Exception as exc:
            print("account menu not opened:", exc)

        # do not close: this is the user's real browser, just disconnect
    return 0


if __name__ == "__main__":
    sys.exit(main())
