#!/usr/bin/env python3
"""
One-time Instagram session setup.
Run this ONCE locally on your PC to generate a session file.
The session file will be committed to the repo so CI can use it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import config


def main():
    if not config.IG_USERNAME or not config.IG_PASSWORD:
        print("❌ Set IG_USERNAME and IG_PASSWORD in .env first!")
        sys.exit(1)

    print(f"📱 Instagram: logging in as {config.IG_USERNAME}…")
    print("   If Instagram asks for verification, enter the code sent to your phone/email.\n")

    from instagrapi import Client

    cl = Client()
    cl.set_user_agent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    cl.delay_range = [1, 3]

    def challenge_handler(username, challenge_type):
        print(f"\n⚠ Verification required for {username}")
        print(f"   Type: {challenge_type}")
        code = input("   Enter code from email/phone: ").strip()
        return code

    cl.challenge_code_handler = challenge_handler

    try:
        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
    except Exception as e:
        print(f"\n❌ Login failed: {e}")
        print("\nTroubleshooting:")
        print("   1. Open instagram.com in a browser and log in manually")
        print("   2. Check if Instagram sent you a security email")
        print("   3. Approve the login attempt from the notification on your phone")
        print("   4. Then run this script again")
        sys.exit(1)

    # Save session
    settings_path = config.CACHE_DIR / "ig_settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    cl.dump_settings(str(settings_path))
    print(f"\n✅ Session saved to {settings_path}")
    print("   Now commit and push this file so CI can use it:")
    print(f"   git add {settings_path}")
    print("   git commit -m 'Add Instagram session'")
    print("   git push")


if __name__ == "__main__":
    main()