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
    Parses structured responses containing:
    TITLE: <title>
    NARRATION: <script>
    EMPHASIS: <comma-separated words>
    """
    result = {
        "title": default_title,
        "narration": "",
        "emphasis": []
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
        elif current_field == "narration":
            narration_lines.append(line_strip)
        elif current_field == "title":
            result["title"] += " " + line_strip
            
    result["narration"] = " ".join([l for l in narration_lines if l]).strip()
    
    # Fallback if parsing failed to extract narration
    if not result["narration"]:
        # If no tags, assume the entire response is the narration
        result["narration"] = response.strip()
        
    # Clean up formatting
    result["narration"] = strip_markdown(strip_emojis(result["narration"]))
    result["title"] = strip_markdown(strip_emojis(result["title"]))
    
    # Generate fallback emphasis if none was specified
    if not result["emphasis"]:
        result["emphasis"] = extract_emphasis_from_text(result["narration"])
        
    return result
