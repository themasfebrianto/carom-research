#!/usr/bin/env python
"""Open the Connect menu in the existing Colab tab and inspect runtime types."""

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
        page = None
        for pg in ctx.pages:
            if "Untitled0" in pg.title() or "/drive/" in pg.url:
                page = pg
                break
        if page is None:
            print("notebook tab not found")
            return 1
        page.bring_to_front()
        # close release notes if present
        try:
            page.get_by_label("Close").first.click(timeout=3000)
        except Exception:
            pass
        page.get_by_text("Connect", exact=True).first.click(timeout=15000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "nb_04_connect_menu.png"), full_page=False)
        items = []
        for loc in page.get_by_role("menuitem").all():
            try:
                items.append(loc.inner_text(timeout=1500))
            except Exception:
                pass
        print("menu items:", items)
        try:
            page.get_by_text("Change runtime type", exact=False).first.click(timeout=10000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "nb_05_runtime_dialog.png"), full_page=False)
            print("dialog opened")
        except Exception as exc:
            print("change runtime click failed:", exc)
            page.screenshot(path=str(OUT / "nb_05_fail.png"), full_page=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
