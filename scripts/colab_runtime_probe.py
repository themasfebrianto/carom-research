#!/usr/bin/env python
"""Open a new Colab notebook in the running Brave and inspect runtime options."""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "out" / "colab_probe"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        page.goto("https://colab.research.google.com/#create=true", wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(12000)
        print("url:", page.url)
        print("title:", page.title())
        page.screenshot(path=str(OUT / "nb_01_new.png"), full_page=False)

        page.get_by_text("Runtime", exact=True).first.click(timeout=15000)
        page.wait_for_timeout(1000)
        page.screenshot(path=str(OUT / "nb_02_runtime_menu.png"), full_page=False)
        page.get_by_text("Change runtime type", exact=False).first.click(timeout=15000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "nb_03_runtime_dialog.png"), full_page=False)
        try:
            print("dialog text:")
            print(" ".join(page.inner_text("body").split())[-2500:])
        except Exception as exc:
            print("inner_text failed:", exc)
        # keep the tab open for the next step
    return 0


if __name__ == "__main__":
    sys.exit(main())
