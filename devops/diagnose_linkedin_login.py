from playwright.sync_api import sync_playwright
import time
import os
import platform


def _detect_chrome_profile():
    """Return the OS-default Chrome user-data directory, or "" if unknown.

    Never hardcodes a machine-specific path: the location is derived from
    the OS conventions (LOCALAPPDATA on Windows, ~/Library on macOS,
    ~/.config on Linux).
    """
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(base, "Google", "Chrome", "User Data") if base else ""
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Google/Chrome")
    else:  # Linux and others
        return os.path.expanduser("~/.config/google-chrome")


# Explicit override via CHROME_PROFILE_PATH env var; otherwise auto-detect by OS.
CHROME_PROFILE = os.environ.get("CHROME_PROFILE_PATH", "") or _detect_chrome_profile()

def check_password_toggle(page):
    toggle = page.locator("button[aria-label='Show password'], button[aria-label='Hide password']")
    return toggle.count() > 0

def main():
    print("\n=== LinkedIn Login Diagnostic ===\n")

    with sync_playwright() as playwright:
        print("Launching Chrome with persistent profile...")

        browser = playwright.chromium.launch_persistent_context(
    user_data_dir=CHROME_PROFILE,
    channel="chrome",
    headless=True,
    args=[
        "--window-size=1280,900",
        "--disable-infobars",
        "--disable-dev-shm-usage",
    ]
)
        page = browser.new_page()

        print("Navigating to LinkedIn login page...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)


        time.sleep(3)

        print("\n--- Checking for password Show/Hide toggle ---")
        if check_password_toggle(page):
            print("✔ Password toggle FOUND — full login page loaded.")
        else:
            print("❌ Password toggle NOT FOUND — restricted login page detected.")

        print("\nDiagnostic complete.\n")

if __name__ == "__main__":
    main()
