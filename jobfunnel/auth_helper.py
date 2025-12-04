#!/usr/bin/env python3
"""Authentication helper script for JobFunnel.

This script opens a headed browser window for users to manually log in to
job sites that require authentication (LinkedIn, Glassdoor). After login,
it saves the session state to a storageState JSON file that JobFunnel can
use for authenticated scraping.

IMPORTANT: JobFunnel NEVER stores or transmits your credentials. This script
only saves session cookies after you log in manually. The storageState file
remains on your local machine.

Usage:
    python -m jobfunnel.auth_helper linkedin
    python -m jobfunnel.auth_helper glassdoor
    python -m jobfunnel.auth_helper linkedin --output /path/to/linkedin.auth.json
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROVIDER_CONFIG = {
    "linkedin": {
        "login_url": "https://www.linkedin.com/login",
        "success_indicator": "feed",  # URL contains this after successful login
        "default_output": "linkedin.auth.json",
        "display_name": "LinkedIn",
    },
    "glassdoor": {
        "login_url": "https://www.glassdoor.com/profile/login_input.htm",
        "success_indicator": "member",  # URL contains this after successful login
        "default_output": "glassdoor.auth.json",
        "display_name": "Glassdoor",
    },
}


def run_auth_flow(provider: str, output_path: str) -> bool:
    """Run the authentication flow for a provider.

    Args:
        provider: The provider name (linkedin, glassdoor)
        output_path: Path to save the storageState JSON file

    Returns:
        True if authentication succeeded, False otherwise
    """
    if provider not in PROVIDER_CONFIG:
        print(f"Error: Unknown provider '{provider}'")
        print(f"Supported providers: {', '.join(PROVIDER_CONFIG.keys())}")
        return False

    config = PROVIDER_CONFIG[provider]
    display_name = config["display_name"]

    print(f"\n{'=' * 60}")
    print(f"  {display_name} Authentication Helper")
    print(f"{'=' * 60}\n")
    print("IMPORTANT: JobFunnel never stores or transmits your credentials.")
    print("This script only saves session cookies after you log in manually.\n")
    print(f"1. A browser window will open to {display_name}'s login page")
    print("2. Log in with your credentials")
    print("3. Complete any 2FA/CAPTCHA if required")
    print("4. Once logged in, return here and press Enter")
    print(f"\nSession will be saved to: {output_path}\n")

    input("Press Enter to open the browser...")

    with sync_playwright() as p:
        # Launch a headed browser (user can see it)
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--enable-sandbox",
            ],
        )

        # Create a new context (fresh session)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )

        page = context.new_page()

        try:
            # Navigate to login page
            print(f"\nNavigating to {display_name} login page...")
            page.goto(config["login_url"], timeout=60000)

            # Wait for user to log in
            print(f"\nPlease log in to {display_name} in the browser window.")
            print("After you're logged in, return here and press Enter.\n")
            input("Press Enter after you've successfully logged in...")

            # Check if login was successful by looking at URL
            current_url = page.url
            if config["success_indicator"] in current_url.lower():
                print(f"\nLogin appears successful! (URL: {current_url})")
            else:
                print(f"\nNote: Could not verify login status (URL: {current_url})")
                print("If you're logged in, the session will still be saved.")

            # Save the storage state
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            context.storage_state(path=str(output_file))
            print(f"\nSession saved to: {output_file.absolute()}")
            print("\nYou can now use this file in your JobFunnel settings.yaml:")
            print("\n  auth:")
            print(f'    {provider}_storage_state: "{output_file.absolute()}"')
            print("\nDone!")
            return True

        except Exception as e:
            print(f"\nError during authentication: {e}")
            return False

        finally:
            context.close()
            browser.close()


def main() -> int:
    """Main entry point for the auth helper."""
    parser = argparse.ArgumentParser(
        description="Generate authentication files for JobFunnel job scrapers.",
        epilog="Example: python -m jobfunnel.auth_helper linkedin",
    )

    parser.add_argument(
        "provider",
        choices=list(PROVIDER_CONFIG.keys()),
        help="The job site to authenticate with",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output path for the storageState JSON file (default: <provider>.auth.json)",
    )

    args = parser.parse_args()

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = PROVIDER_CONFIG[args.provider]["default_output"]

    # Run the auth flow
    success = run_auth_flow(args.provider, output_path)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
