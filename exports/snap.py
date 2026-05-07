"""Capture full-page Streamlit renders + clean text."""
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent
URL = "http://localhost:8765/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    # Landing
    page.goto(URL, wait_until="networkidle")
    page.wait_for_selector("text=合理價計算機", timeout=20000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "screenshot-landing-full.png"), full_page=True, timeout=60000)
    landing_text = page.evaluate("() => document.body.innerText")
    (OUT / "page-landing.txt").write_text(landing_text, encoding="utf-8")

    # Click 開始分析
    page.click("button:has-text('開始分析')", timeout=10000)
    page.wait_for_selector("text=候選清單", timeout=120000)
    page.wait_for_timeout(3000)
    # Open the calculator expander to capture its rendered state too
    summaries = page.locator("summary:has-text('合理價計算機')")
    if summaries.count() > 0:
        try:
            # if it's collapsed, click to open
            summaries.first.click()
            page.wait_for_timeout(1500)
        except Exception:
            pass
    page.screenshot(path=str(OUT / "screenshot-analysis-full.png"), full_page=True, timeout=60000)
    analysis_text = page.evaluate("() => document.body.innerText")
    (OUT / "page-analysis.txt").write_text(analysis_text, encoding="utf-8")

    browser.close()

print("DONE")
print("Files in exports/:")
for f in sorted(OUT.iterdir()):
    print(f"  {f.name}: {f.stat().st_size:,} bytes")
