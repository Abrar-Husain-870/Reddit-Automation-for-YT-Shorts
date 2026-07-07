"""
Generate brainrot scripts for GTA V clips using Groq LLM (free tier).
Target: 40-65 words, hook-first, with emphasis keywords for kinetic captions.
No emojis — clean text only for TTS compatibility.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from groq import Groq

import config

USER_SYSTEM_PROMPT = (
    "You write viral brainrot short-form video scripts. "
    "Your style: chaotic, FUNNY, relatable gamer humor. "
    "CRITICAL: Do NOT use any emojis or special unicode characters. "
    "Use ONLY plain text words and punctuation. "
    "Structure each script EXACTLY as: HOOK | BODY | PUNCHLINE | EMPHASIS\n"
    "HOOK: A single short sentence (5-10 words) that grabs attention immediately. "
    "Ask a question or make a shocking statement. "
    "BODY: 3-5 short punchy lines that tell a quick mini-story with a setup and escalation. "
    "PUNCHLINE: A single funny line (5-10 words) that closes the video. "
    "Total script is EXACTLY 40-65 words across HOOK + BODY + PUNCHLINE. "
    "This is for a 15-22 second voiceover. "
    "Use ALL CAPS for 2-3 KEY WORDS total that should be visually emphasized. "
    "EMPHASIS: List exactly 2-3 words (without punctuation) that were in ALL CAPS, comma-separated. "
    "Sound like a GENUINE GAMER reacting to what's happening on screen. "
    "Examples of HOOK style: "
    "'Ever wonder what happens when you PISS OFF an NPC?' "
    "'Watch this GTA V NPC commit a CRIME better than me.' "
    "'This is why GTA V is the BEST game ever made.' "
    "Then BODY tells what happens. Then PUNCHLINE delivers the laugh."
    "Be FUNNY. Be RELATABLE. Think like a gamer streaming to friends."
)

# Fallback narration for when Groq API fails
FALLBACK_NARRATION = (
    "EVER wonder what happens when you mess with GTA V physics? "
    "Bro I was just driving NORMAL and a trash truck SPAWNS on my car. "
    "This game is PEAK chaos and I love every second of it."
)
FALLBACK_EMPHASIS = "EVER, NORMAL, SPAWNS, PEAK"


def _strip_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def _parse_structured_response(response: str) -> dict:
    """Parse the structured LLM response into components.
    Handles both strict HOOK|BODY|PUNCHLINE format and free-form text.
    """
    result = {
        "hook": "",
        "body": "",
        "punchline": "",
        "emphasis": [],
        "full_narration": "",
        "title": "GTA V BRAINROT",
    }

    lines = response.splitlines()
    current_section = None
    sections = {}
    found_any_label = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("HOOK:"):
            found_any_label = True
            current_section = "hook"
            sections["hook"] = line.split(":", 1)[1].strip()
        elif upper.startswith("BODY:"):
            found_any_label = True
            current_section = "body"
            sections["body"] = line.split(":", 1)[1].strip()
        elif upper.startswith("PUNCHLINE:"):
            found_any_label = True
            current_section = "punchline"
            sections["punchline"] = line.split(":", 1)[1].strip()
        elif upper.startswith("EMPHASIS:"):
            found_any_label = True
            current_section = "emphasis"
            raw = line.split(":", 1)[1].strip()
            result["emphasis"] = [w.strip().upper() for w in raw.split(",") if w.strip()]
        elif upper.startswith("NARRATION:"):
            found_any_label = True
            result["full_narration"] = line.split(":", 1)[1].strip()
        elif upper.startswith("TITLE:"):
            found_any_label = True
            result["title"] = line.split(":", 1)[1].strip()[:60]
        elif current_section and line:
            sections[current_section] = sections.get(current_section, "") + " " + line

    # Build structured result from sections
    if sections.get("hook") or sections.get("body") or sections.get("punchline"):
        result["hook"] = sections.get("hook", "")
        result["body"] = sections.get("body", "")
        result["punchline"] = sections.get("punchline", "")
        parts = [p for p in [result["hook"], result["body"], result["punchline"]] if p]
        result["full_narration"] = " ".join(parts)
    elif result["full_narration"]:
        pass  # Already set from NARRATION: label
    elif found_any_label:
        # Had labels but no content - shouldn't happen but handle gracefully
        result["full_narration"] = response
    else:
        # No labels at all - treat entire response as free-form narration
        # Try to extract title from last line if it looks like a title
        result["full_narration"] = response
        # Check if last line looks like a title (short, no punctuation)
        last_line = lines[-1].strip() if lines else ""
        if last_line and len(last_line.split()) <= 8 and not last_line.endswith((".", "!", "?")):
            result["title"] = last_line[:60]
            # Remove title from narration
            result["full_narration"] = "\n".join(lines[:-1]).strip()

    # Generate title from HOOK if no explicit TITLE was found
    if result["title"] == "GTA V BRAINROT" and result.get("hook"):
        # Use hook as title (truncate to 60 chars if needed)
        hook_title = result["hook"].rstrip(".!?")
        hook_title = re.sub(r'[^\w\s\'-]', '', hook_title).strip()
        if hook_title:
            # Style prefix based on content
            result["title"] = hook_title[:60]

    # If still no title, generate from first line of narration
    if result["title"] == "GTA V BRAINROT" and result["full_narration"]:
        first_sentence = result["full_narration"].split(".")[0].strip()
        if first_sentence and len(first_sentence) > 5:
            first_sentence = re.sub(r'[^\w\s\'-]', '', first_sentence).strip()
            if len(first_sentence) > 55:
                first_sentence = first_sentence[:55] + "..."
            result["title"] = first_sentence

    # Always extract emphasis from narration as fallback
    if not result["emphasis"] and result["full_narration"]:
        result["emphasis"] = _extract_emphasis_from_text(result["full_narration"])

    return result


def _extract_emphasis_from_text(text: str) -> list[str]:
    """Extract ALL CAPS words as emphasis targets."""
    words = text.split()
    caps_words = [w.strip(".,!?;:\"'") for w in words if w.isupper() and len(w) > 2]
    # Deduplicate while preserving order
    seen = set()
    return [w for w in caps_words if not (w in seen or seen.add(w))][:5]


def generate_brainrot_script(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str, list[str]]:
    """
    Generate a brainrot script.
    Returns: (full_narration, title, emphasis_words)
    """
    api_key = config.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not set!")
        sys.exit(1)

    client = Groq(api_key=api_key)

    user_prompt = (
        f"Write a FUNNY brainrot script for this GTA V gameplay clip.\n\n"
        f"Requirements:\n"
        f"- Total 40-65 words across HOOK + BODY + PUNCHLINE\n"
        f"- HOOK: grab attention in 5-10 words (question or shocking statement)\n"
        f"- BODY: 3-5 short lines telling what happened\n"
        f"- PUNCHLINE: funny closing line\n"
        f"- Use ALL CAPS on 2-3 key words for emphasis\n"
        f"- NO EMOJIS whatsoever - plain text only\n"
        f"- Sound like a real gamer reacting\n"
        f"- Reference GTA: NPCs, cops, chaos, physics glitches\n\n"
        f"Format EXACTLY like this:\n"
        f"HOOK: <attention grabber, 5-10 words>\n"
        f"BODY: <3-5 short lines, 25-45 words total>\n"
        f"PUNCHLINE: <funny closing, 5-10 words>\n"
        f"EMPHASIS: <comma-separated list of the 2-3 ALL CAPS words>\n"
        f"TITLE: <clickbait title under 60 chars>"
    )

    print(f"🤖 Groq: generating {style} brainrot script (target 40-65 words)…")

    best_result = {
        "full_narration": "",
        "title": "GTA V BRAINROT",
        "emphasis": [],
        "word_count": 0,
    }

    for attempt in range(2):
        try:
            completion = client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": USER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.95,
                max_tokens=600,
                timeout=30,
            )
        except Exception as e:
            print(f"   ⚠ Groq API error (attempt {attempt+1}): {e}")
            if attempt == 1:
                print(f"   ⚠ Using fallback narration")
                return FALLBACK_NARRATION, "GTA V BRAINROT", ["EVER", "NORMAL", "SPAWNS", "PEAK"]
            continue

        response = completion.choices[0].message.content.strip()

        # Parse structured response
        parsed = _parse_structured_response(response)

        # Strip formatting
        narration = _strip_emojis(parsed["full_narration"])
        narration = narration.replace("**", "").replace("__", "").replace("*", "")
        title = _strip_emojis(parsed["title"])
        title = title.replace("**", "").replace("__", "").replace("*", "")

        # Get emphasis words
        emphasis = parsed["emphasis"]
        if not emphasis:
            emphasis = _extract_emphasis_from_text(narration)

        wc = len(narration.split())
        if wc > best_result["word_count"] and wc >= 30:
            best_result["full_narration"] = narration
            best_result["title"] = title or "GTA V BRAINROT"
            best_result["emphasis"] = emphasis
            best_result["word_count"] = wc

        if 35 <= wc <= 75:
            break
        user_prompt += "\n\nMake it shorter and punchier! MUST be 40-65 words."

    # If we got nothing useful, use fallback
    if not best_result["full_narration"]:
        print("   ⚠ No valid script generated, using fallback")
        return FALLBACK_NARRATION, "GTA V BRAINROT", ["EVER", "NORMAL", "SPAWNS", "PEAK"]

    print(f"   📝 {best_result['word_count']} words, {len(best_result['emphasis'])} emphasis words")
    return best_result["full_narration"], best_result["title"], best_result["emphasis"]


# Backward compatibility for old code that expects 2 return values
def generate_brainrot_script_legacy(
    clip_description: str = "",
    style: str = "chaotic",
) -> tuple[str, str]:
    """Legacy wrapper that returns (narration, title) without emphasis."""
    narration, title, _ = generate_brainrot_script(clip_description, style)
    return narration, title


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="chaotic")
    args = ap.parse_args()
    n, t, e = generate_brainrot_script(style=args.style)
    print(f"\n✅ {len(n.split())} words: {n}")
    print(f"📌 {t}")
    print(f"🔍 Emphasis: {e}")