"""End-to-end smoke check: verify Streamlit actually renders PanLigra's Home page."""
import sys
from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18763/"

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True, args=["--disable-gpu"])
    try:
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.get_by_text("Scientific workspace", exact=True).wait_for(timeout=45000)
        if page.get_by_text("Not Found", exact=True).count():
            raise RuntimeError("Streamlit displays Not Found instead of PanLigra home")
        if page.get_by_text("Page not found", exact=False).count():
            raise RuntimeError("Streamlit displays Page not found")
        print("PASS: PanLigra Home page rendered; no Not Found error")
    finally:
        browser.close()
