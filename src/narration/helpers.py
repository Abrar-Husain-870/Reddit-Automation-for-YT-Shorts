import re
from typing import Dict, List, Tuple

def strip_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"
        "\u2600-\u27BF"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub("", text).strip()


def strip_markdown(text: str) -> str:
    """Remove markdown symbols like **, __, *, _, etc."""
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    text = text.replace("`", "").replace("#", "")
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove links/URLs
    text = re.sub(r"http\S+", "", text)
    return text.strip()


def extract_emphasis_from_text(text: str, limit: int = 5) -> List[str]:
    """Extract ALL CAPS words from text as emphasis targets, ignoring common small words."""
    words = text.split()
    caps_words = []
    seen = set()
    for w in words:
        cleaned = w.strip(".,!?;:\"'()[]{}*-")
        if cleaned.isupper() and len(cleaned) > 2 and cleaned not in seen:
            seen.add(cleaned)
            caps_words.append(cleaned)
    return caps_words[:limit]


def parse_structured_response(response: str, default_title: str = "Reddit Story") -> Dict[str, any]:
    """
    Parses structured responses containing script and metadata tags.
    """
    result = {
        "title": default_title,
        "narration": "",
        "emphasis": [],
        "yt_title": "",
        "yt_hook": "",
        "yt_summary": "",
        "yt_category": "",
        "yt_content_tags": []
    }
    
    lines = response.splitlines()
    current_field = None
    narration_lines = []
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        upper_line = line_strip.upper()
        if upper_line.startswith("TITLE:"):
            result["title"] = line_strip.split(":", 1)[1].strip()
            current_field = "title"
        elif upper_line.startswith("NARRATION:"):
            narration_lines.append(line_strip.split(":", 1)[1].strip())
            current_field = "narration"
        elif upper_line.startswith("EMPHASIS:"):
            raw_emp = line_strip.split(":", 1)[1].strip()
            result["emphasis"] = [w.strip().upper() for w in raw_emp.split(",") if w.strip()]
            current_field = "emphasis"
        elif upper_line.startswith("YT_TITLE:"):
            result["yt_title"] = line_strip.split(":", 1)[1].strip()
            current_field = "yt_title"
        elif upper_line.startswith("YT_HOOK:"):
            result["yt_hook"] = line_strip.split(":", 1)[1].strip()
            current_field = "yt_hook"
        elif upper_line.startswith("YT_SUMMARY:"):
            result["yt_summary"] = line_strip.split(":", 1)[1].strip()
            current_field = "yt_summary"
        elif upper_line.startswith("YT_CATEGORY:"):
            result["yt_category"] = line_strip.split(":", 1)[1].strip()
            current_field = "yt_category"
        elif upper_line.startswith("YT_CONTENT_TAGS:"):
            raw_tags = line_strip.split(":", 1)[1].strip()
            result["yt_content_tags"] = [t.strip() for t in raw_tags.split(",") if t.strip()]
            current_field = "yt_content_tags"
        elif current_field == "narration":
            narration_lines.append(line_strip)
        elif current_field == "title":
            result["title"] += " " + line_strip
        elif current_field == "yt_title":
            result["yt_title"] += " " + line_strip
        elif current_field == "yt_hook":
            result["yt_hook"] += " " + line_strip
        elif current_field == "yt_summary":
            result["yt_summary"] += " " + line_strip
            
    result["narration"] = " ".join([l for l in narration_lines if l]).strip()
    
    # Fallback if parsing failed to extract narration
    if not result["narration"]:
        # If no tags, assume the entire response is the narration
        result["narration"] = response.strip()
        
    # Clean up formatting
    result["narration"] = strip_markdown(strip_emojis(result["narration"]))
    result["title"] = strip_markdown(strip_emojis(result["title"]))
    result["yt_title"] = strip_markdown(strip_emojis(result["yt_title"]))
    result["yt_hook"] = strip_markdown(strip_emojis(result["yt_hook"]))
    result["yt_summary"] = strip_markdown(strip_emojis(result["yt_summary"]))
    
    # Generate fallback emphasis if none was specified
    if not result["emphasis"]:
        result["emphasis"] = extract_emphasis_from_text(result["narration"])
        
    return result


PROFANITY_REPLACEMENTS = [
    (re.compile(r"\bbullshit\b", re.IGNORECASE), "nonsense"),
    (re.compile(r"\bhorseshit\b", re.IGNORECASE), "nonsense"),
    (re.compile(r"\bdipshit\b", re.IGNORECASE), "fool"),
    (re.compile(r"\bshithead\b", re.IGNORECASE), "fool"),
    (re.compile(r"\bshitting\b", re.IGNORECASE), "messing"),
    (re.compile(r"\bshitted\b", re.IGNORECASE), "messed"),
    (re.compile(r"\bshitty\b", re.IGNORECASE), "terrible"),
    (re.compile(r"\bshit\b", re.IGNORECASE), "stuff"),
    (re.compile(r"\bmotherfuckers?\b", re.IGNORECASE), "jerks"),
    (re.compile(r"\bfucking\b", re.IGNORECASE), "freaking"),
    (re.compile(r"\bfucked\b", re.IGNORECASE), "messed"),
    (re.compile(r"\bfucker\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bfuckup\b", re.IGNORECASE), "mistake"),
    (re.compile(r"\bfuck\b", re.IGNORECASE), "freak"),
    (re.compile(r"\bbitching\b", re.IGNORECASE), "complaining"),
    (re.compile(r"\bbitch(es)?\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bassholes?\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bdumbass(es)?\b", re.IGNORECASE), "fool"),
    (re.compile(r"\bjackass(es)?\b", re.IGNORECASE), "fool"),
    (re.compile(r"\bbastards?\b", re.IGNORECASE), "scoundrel"),
    (re.compile(r"\bpuss(y|ies)\b", re.IGNORECASE), "coward"),
    (re.compile(r"\bcocks?\b", re.IGNORECASE), "fool"),
    (re.compile(r"\bdicks?\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bdickheads?\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bpricks?\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bsluts?\b", re.IGNORECASE), "person"),
    (re.compile(r"\bwhores?\b", re.IGNORECASE), "person"),
    (re.compile(r"\bcrap\b", re.IGNORECASE), "junk"),
    (re.compile(r"\bdamn\b", re.IGNORECASE), "darn"),
    (re.compile(r"\bf\*ck\b", re.IGNORECASE), "freak"),
    (re.compile(r"\bsh\*t\b", re.IGNORECASE), "stuff"),
    (re.compile(r"\bb\*tch\b", re.IGNORECASE), "jerk"),
    (re.compile(r"\bd\*ck\b", re.IGNORECASE), "jerk"),
]


def _match_case(replacement: str, original: str) -> str:
    """Match uppercase/capitalized casing of original word."""
    if original.isupper():
        return replacement.upper()
    if original.istitle():
        return replacement.capitalize()
    return replacement.lower()


def sanitize_profanity_in_script(text: str) -> str:
    """Replace profanity words with clean family-friendly synonyms, preserving case."""
    if not text:
        return text
    sanitized = text
    for pattern, replacement in PROFANITY_REPLACEMENTS:
        def replace_fn(match):
            return _match_case(replacement, match.group(0))
        sanitized = pattern.sub(replace_fn, sanitized)
    return sanitized

