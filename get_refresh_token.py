#!/usr/bin/env python3
"""
Helper script: Generate a YouTube OAuth refresh token for a new channel.

Usage:
    python get_refresh_token.py

Then paste the printed REFRESH_TOKEN into your .env file.
Uses the same YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE from your .env.
"""
from __future__ import annotations

import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

import config


def main() -> None:
    if not config.YT_CLIENT_ID or "your_client_id" in config.YT_CLIENT_ID:
        print("❌ Set YT_CLIENT_ID and YT_CLIENT_SECRET_VALUE in .env first!")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    client_config = {
        "installed": {
            "client_id": config.YT_CLIENT_ID,
            "client_secret": config.YT_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    print("=" * 60)
    print("🔑 YOUTUBE REFRESH TOKEN GENERATOR")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: When the browser opens, sign in with your")
    print("   NEW channel's email address (not your old one)!")
    print()
    print("   Then click 'Continue' to grant access.")
    print()

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    print()
    print("=" * 60)
    print("✅ SUCCESS! Here is your new refresh token:")
    print()
    print(f"   {creds.refresh_token}")
    print()
    print("=" * 60)
    print()
    print("📌 Add this to your .env file:")
    print(f'   YT_REFRESH_TOKEN="{creds.refresh_token}"')
    print()
    print("   Or if keeping both old and new tokens:")
    print(f'   YT_REFRESH_TOKEN_GTA="{creds.refresh_token}"')
    print()


if __name__ == "__main__":
    main()