import sys

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
BASE_URL = BASE_URL.rstrip("/")

try:
    from playwright.sync_api import sync_playwright
except Exception:
    print("Playwright is not installed. Run:")
    print("  python -m pip install playwright")
    print("  python -m playwright install")
    sys.exit(2)


NAV_SELECTORS = [
    "a.icon-btn[title='Home']",
    "a.icon-btn[title='Explore']",
    "a.icon-btn[title='Create']",
    "a.icon-btn[title='Messenger']",
    "a.icon-btn[title='Live']",
    "a.icon-btn[title='Account']",
    "a.icon-btn[title='Settings']",
    "a.icon-btn[title='Logout']",
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL + "/feed", wait_until="domcontentloaded")
        page.set_default_timeout(5000)

        failures = 0
        for selector in NAV_SELECTORS:
            try:
                page.locator(selector).first.click()
                page.wait_for_load_state("domcontentloaded")
            except Exception as err:
                failures += 1
                print("FAIL", selector, "->", err)
            finally:
                page.goto(BASE_URL + "/feed", wait_until="domcontentloaded")

        browser.close()

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
