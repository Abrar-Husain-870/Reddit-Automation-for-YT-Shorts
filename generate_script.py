"""
Generate brainrot scripts for GTA V clips using Groq LLM (free tier).
Target: 70-120 words, funny + engaging brainrot style.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from groq import Groq

import config

USER_SYSTEM_PROMPT = (
    "You write viral brainrot short-form video scripts. "
    "Your style: chaotic, FUNNY, relatable gamer humor. "
    "Use short punchy lines. Each line is 5-10 words. "
    "Total script is EXACTLY 8-15 lines (70-120 words total). "
    "This is for a 25-35 second voiceover. "
    "Use ALL CAPS for the FUNNY/IMPORTANT words. "
    "Add emojis between thoughts. "
    "Sound like a GENUINE GAMER reacting to what's happening on screen. "
    "NOT random words - tell a MINI STORY with a setup and punchline. "
    "Examples of the style (but be original): "
    "'Bro JUST WATCH this NPC... he's about to DO something STUPID... oh NO he DID NOT just do that HAHAHA' "
    "'Me: driving NORMAL... GTA V: LETS THROW A TRASH TRUCK at your face' "
    "Be FUNNY. Be RELATABLE. Think like a gamer streaming to friends."
)


def generate_brainrot_script(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str]:
    api_key = config.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set!")
        sys.exit(1)

    client = Groq(api_key=api_key)

    user_prompt = (
        f"Write a FUNNY brainrot script for this GTA V gameplay clip.\n\n"
        f"Requirements:\n"
        f"- 8-15 short punchy lines (total 70-120 words)\n"
        f"- Tell a mini-story: setup → escalation → funny punchline\n"
        f"- Use ALL CAPS for dramatic/funny emphasis\n"
        f"- Add emojis 🚗💥😱🤣\n"
        f"- Sound like a real gamer reacting, not a robot\n"
        f"- Reference things that happen in GTA: NPCs, cops, chaos, physics glitches, etc.\n"
        f"- The funnier the better\n\n"
        f"Format EXACTLY like this:\n"
        f"NARRATION: <your 70-120 word script>\n"
        f"TITLE: <clickbait title under 60 chars>"
    )

    print(f"🤖 Groq: generating {style} brainrot script (target 70-120 words)…")

    best_narration = ""
    best_title = "GTA V BRAINROT 🎮🔥"
    best_wc = 0

    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.95,
                max_tokens=800,
                timeout=30,  # 30 second timeout for Groq API
            )
        except Exception as e:
            print(f"   ⚠ Groq API error (attempt {attempt+1}): {e}")
            if attempt == 1:
                # Use fallback narration
                best_narration = "When the GTA V physics engine decides to absolutely DESTROY your day 💀 Like bro I was just driving NORMAL and then BOOM a trash truck spawns on my head HAHAHA this game is PEAK chaos I love it 😂🚗💥"
                best_title = "GTA V BRAINROT 🔥"
                best_wc = len(best_narration.split())
                print(f"   ⚠ Using fallback narration ({best_wc} words)")
                break
            continue

        response = completion.choices[0].message.content.strip()

        narration = ""
        title = "GTA V BRAINROT 🎮🔥"
        for line in response.splitlines():
            line = line.strip()
            if line.upper().startswith("NARRATION:"):
                narration = line.split(":", 1)[1].strip().replace("**", "").replace("__", "")
            elif line.upper().startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()[:60]

        if not narration:
            narration = response.replace("**", "").replace("__", "")
            for p in ["NARRATION:", "Narration:", "narration:"]:
                if narration.upper().startswith(p.upper()):
                    narration = narration[len(p):].strip()

        wc = len(narration.split())
        if wc > best_wc:
            best_narration = narration
            best_title = title
            best_wc = wc

        if wc >= 70:
            break
        user_prompt += "\n\nToo short! MUST be 70-120 words. Add more funny lines."

    print(f"   📝 {best_wc} words")
    return best_narration, best_title


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="chaotic")
    args = ap.parse_args()
    n, t = generate_brainrot_script(style=args.style)
    print(f"\n✅ {len(n.split())} words: {n[:120]}...")
    print(f"📌 {t}")