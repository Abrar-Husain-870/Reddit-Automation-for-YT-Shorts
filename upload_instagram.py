"""
Upload rendered GTA VI brainrot shorts to Instagram Reels.
Uses instagrapi (unofficial but free) for posting.
All API calls have timeouts to prevent indefinite hangs on CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

import config

IG_TIMEOUT = 60  # 1 minute timeout for Instagram operations


def upload_reel(
    video_path: Path,
    caption: str = "",
) -> str:
    """
    Upload a short to Instagram Reels using instagrapi.
    
    Args:
        video_path: Path to the rendered MP4.
        caption: Reel caption with hashtags.
    
    Returns:
        Media ID on success, empty string on failure.
    """
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return ""

    if not config.IG_USERNAME or not config.IG_PASSWORD:
        print("⚠ IG_USERNAME / IG_PASSWORD not set — skipping Instagram upload")
        return ""

    print(f"📱 Instagram: logging in as {config.IG_USERNAME}…")

    try:
        from instagrapi import Client
        from instagrapi.exceptions import LoginRequired, ClientError

        cl = Client()
        # Set a timeout on IG requests
        import socket
        socket.setdefaulttimeout(IG_TIMEOUT)
        cl.delay_range = [1, 3]  # Respect rate limits

        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
        print("   ✅ Logged in")

        # Build caption with hashtags
        hashtags = (
            "#GTAVI #GTA6 #GamingShorts #Brainrot #GTA6Gameplay "
            "#GamingMemes #Reels #GTA6Moment #RockstarGames"
        )
        full_caption = f"{caption}\n.\n{hashtags}" if caption else hashtags

        print("   📤 Uploading Reel…")
        result = cl.clip_upload(str(video_path), full_caption)
        media_id = result.id
        print(f"   ✅ Uploaded! Media ID: {media_id}")
        return str(media_id)

    except ImportError:
        print("⚠ instagrapi not installed. Install with: pip install instagrapi")
        return ""
    except Exception as e:
        print(f"❌ Instagram upload failed: {e}")
        return ""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="Path to MP4")
    ap.add_argument("--caption", default="GTA VI BRAINROT 🎮🔥", help="Reel caption")
    args = ap.parse_args()

    upload_reel(Path(args.video), args.caption)