#!/usr/bin/env python3
"""
Reddit to Shorts Automation Pipeline — Master Orchestrator.
Parses settings, coordinates ingestion, narration, voiceover, rendering, and upload.
Robust error handling ensures the pipeline completes even if APIs fail.
"""
from __future__ import annotations

import argparse
import random
import sys
import threading
import time
from pathlib import Path

import config
from src.logger import (
    logger,
    log_stage_start,
    log_stage_finish,
    log_stage_error,
)
from src.reddit.client import get_random_reddit_post, save_processed_id
from src.narration import generate_script_with_fallback
from src.voice import synthesize_voiceover_with_fallback
from src.video import (
    get_background_clip,
    increment_background_usage,
    generate_reddit_card,
    render_short,
)
from src.upload import upload_short, check_scheduler_run

# Global timeout for safety (40 minutes)
PIPELINE_TIMEOUT = 40 * 60


def clean_temp_files() -> None:
    """Clean intermediate temp files in output directory to save space."""
    logger.info("Cleaning up temporary render files...")
    for ext in ["*.ass", "*.mp3", "*.png"]:
        for f in config.OUTPUT_DIR.glob(ext):
            try:
                f.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Could not delete temp file {f.name}: {e}")


def main() -> None:
    # Safe fallback timer to kill hung subprocesses or API hangs
    timer = threading.Timer(
        PIPELINE_TIMEOUT, 
        lambda: (
            log_stage_error("Global Pipeline", "Execution timed out", fatal=True),
            sys.exit(1)
        )
    )
    timer.daemon = True
    timer.start()

    try:
        # ── Argument Parsing ─────────────────────────────────
        ap = argparse.ArgumentParser(
            description="Reddit to Shorts Automation Pipeline"
        )
        ap.add_argument("--no-upload", action="store_true", help="Skip YouTube upload phase")
        ap.add_argument("--force", action="store_true", help="Ignore scheduler slots, run immediately")
        ap.add_argument("--style", default="random", 
                        choices=["random", "chaotic", "meme", "story", "npc"],
                        help="Video/caption styling (default: random)")
        ap.add_argument("--mode", default=None, choices=["natural", "commentary"],
                        help="Narration generation mode (default: from config)")
        ap.add_argument("--subreddit", default=None,
                        help="Override subreddits to fetch from (comma-separated)")
        ap.add_argument("--privacy", default=config.YT_PRIVACY,
                        choices=["public", "unlisted", "private"],
                        help="YouTube video visibility")
        ap.add_argument("--skip-download", action="store_true",
                        help="Skip downloading new background clips from YouTube")
        args = ap.parse_args()

        print("=" * 70)
        print("=== REDDIT TO SHORTS AUTOMATION PIPELINE ===")
        print("=" * 70)

        # ── Step 0: Scheduler Gatekeeping ────────────────────
        log_stage_start("Scheduler Check")
        should_run = check_scheduler_run(force=args.force)
        log_stage_finish("Scheduler Check", {"should_run": should_run})
        
        if not should_run:
            print("\n[INFO] Pipeline run skipped by Scheduler. (Not inside an active time slot).")
            print("   Use '--force' to bypass this check.")
            sys.exit(0)

        # Style & Voice Mapping
        style = args.style
        if style == "random":
            style = random.choice(["chaotic", "meme", "story", "npc"])
            
        style_voices = {
            "chaotic": "en-US-AndrewNeural",
            "meme": "en-US-AndrewNeural",
            "story": "en-US-BrianNeural",
            "npc": "en-US-GuyNeural",
        }
        tts_voice = style_voices.get(style, "en-US-AndrewNeural")

        if args.subreddit:
            config.SUBREDDITS = [s.strip() for s in args.subreddit.split(",") if s.strip()]

        # ── Step 1: Reddit Ingestion ─────────────────────────
        log_stage_start("Reddit Ingestion")
        post = get_random_reddit_post()
        if not post:
            error_msg = "No suitable Reddit posts found matching criteria"
            log_stage_error("Reddit Ingestion", error_msg, fatal=True)
            sys.exit(1)
            
        log_stage_finish("Reddit Ingestion", {
            "id": post.id, 
            "subreddit": post.subreddit, 
            "title": post.title[:40] + "..."
        })

        # ── Step 2: Narration Scripting ──────────────────────
        log_stage_start("Script Generation")
        narration_mode = args.mode or config.NARRATION_MODE
        narration, title, emphasis = generate_script_with_fallback(post, narration_mode, style)
        
        log_stage_finish("Script Generation", {
            "title": title,
            "word_count": len(narration.split()),
            "emphasis_count": len(emphasis)
        })
        logger.info(f"Generated Script Text:\n{narration}\nEmphasis: {emphasis}")

        # ── Step 3: Background Clip Selection ────────────────
        log_stage_start("Background Selection")
        bg_clip = get_background_clip(skip_download=args.skip_download)
        if not bg_clip or not bg_clip.exists():
            error_msg = "Could not retrieve background video clip"
            log_stage_error("Background Selection", error_msg, fatal=True)
            sys.exit(1)
            
        log_stage_finish("Background Selection", {"filename": bg_clip.name})

        # ── Step 4: Reddit Card Overlay Image ────────────────
        log_stage_start("Overlay Generation")
        overlay_path = None
        if config.OVERLAY_REDDIT_SCREENSHOT:
            try:
                overlay_path = generate_reddit_card(post)
                log_stage_finish("Overlay Generation", {"path": str(overlay_path)})
            except Exception as e:
                log_stage_error("Overlay Generation", f"Failed: {e}. Proceeding without overlay.")
                overlay_path = None
        else:
            log_stage_finish("Overlay Generation", {"status": "skipped"})

        # ── Step 5: Voice Synthesis (TTS) ───────────────────
        log_stage_start("Voice Synthesis")
        audio_path = config.OUTPUT_DIR / "voiceover.mp3"
        try:
            audio_dur, sentence_timings = synthesize_voiceover_with_fallback(
                narration, output_path=audio_path, voice=tts_voice
            )
            log_stage_finish("Voice Synthesis", {"duration_s": audio_dur, "sentences": len(sentence_timings)})
        except Exception as e:
            log_stage_error("Voice Synthesis", e, fatal=True)
            sys.exit(1)

        # ── Step 6: FFmpeg Render ────────────────────────────
        log_stage_start("Video Rendering")
        video_path = config.OUTPUT_DIR / "final_short.mp4"
        try:
            render_short(
                clip_path=bg_clip,
                audio_path=audio_path,
                narration=narration,
                overlay_card_path=overlay_path,
                output_path=video_path,
                sentence_timings=sentence_timings,
                style=style,
                emphasis_words=emphasis
            )
            log_stage_finish("Video Rendering", {"output_video": str(video_path)})
        except Exception as e:
            log_stage_error("Video Rendering", e, fatal=True)
            sys.exit(1)

        # ── Step 7: Update Databases ─────────────────────────
        log_stage_start("Database Update")
        save_processed_id(post.id)
        increment_background_usage(bg_clip.name)
        log_stage_finish("Database Update")

        # ── Step 8: Upload YouTube Shorts ────────────────────
        video_id = ""
        if not args.no_upload:
            log_stage_start("YouTube Upload")
            
            # Formulate descriptions
            desc_body = f"Reddit story from r/{post.subreddit}.\n\nOriginal title: {post.title}"
            
            video_id = upload_short(
                video_path=video_path,
                title=title,
                description=desc_body,
                privacy=args.privacy
            )
            
            if video_id:
                log_stage_finish("YouTube Upload", {"video_id": video_id})
            else:
                log_stage_error("YouTube Upload", "Upload failed")
        else:
            log_stage_start("YouTube Upload")
            log_stage_finish("YouTube Upload", {"status": "skipped"})

        # ── Step 9: Instagram Reels Guide ────────────────────
        print()
        print("=" * 70)
        print("=== INSTAGRAM MANUAL UPLOAD GUIDE ===")
        print("=" * 70)
        print(f"Post Description:\n{title}\n\nReddit story from r/{post.subreddit} #reddit #shorts\n")
        print(f"Video File: {video_path}")
        print("=" * 70)

        # Cleanup intermediate files
        clean_temp_files()

        print("\n[SUCCESS] PIPELINE SUCCESSFUL!")
        if video_id:
            print(f"   Published YouTube Short: https://www.youtube.com/shorts/{video_id}")
        print(f"   Video file saved to: {video_path}\n")

    finally:
        timer.cancel()


if __name__ == "__main__":
    main()