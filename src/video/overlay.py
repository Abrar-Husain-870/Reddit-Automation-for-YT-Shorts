import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import config
from src.logger import logger
from src.reddit.models import RedditPost


def _wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within a maximum width in pixels."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        # Get width of current line
        bbox = draw.textbbox((0, 0), line_str, font=font)
        w = bbox[2] - bbox[0]
        
        if w > max_width:
            if len(current_line) == 1:
                # Word itself is too long, force split it
                lines.append(line_str)
                current_line = []
            else:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


def generate_reddit_card(post: RedditPost) -> Path:
    """
    Generate a beautiful dark mode Reddit post card overlay.
    Returns the path to the saved transparent PNG image.
    """
    output_path = config.OUTPUT_DIR / "reddit_card.png"
    
    # ── Dimensions & Padding ─────────────────────────────────
    card_width = 900
    padding = 40
    
    # Fonts loading with fallbacks
    try:
        # Try loading standard windows / unix sans fonts
        font_title = ImageFont.truetype("arialbd.ttf", 36)
        font_meta = ImageFont.truetype("arial.ttf", 24)
        font_meta_bold = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            font_meta = ImageFont.truetype("DejaVuSans.ttf", 24)
            font_meta_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except Exception:
            # Absolute fallback
            font_title = ImageFont.load_default()
            font_meta = ImageFont.load_default()
            font_meta_bold = ImageFont.load_default()

    # Pre-render wrap to calculate dynamic height
    temp_img = Image.new("RGBA", (card_width, 100))
    temp_draw = ImageDraw.Draw(temp_img)
    
    max_text_width = card_width - (padding * 2)
    wrapped_title = _wrap_text(post.title, temp_draw, font_title, max_text_width)
    
    # Title height estimation
    line_spacing = 8
    title_height = 0
    for line in wrapped_title:
        bbox = temp_draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        title_height += h + line_spacing
    title_height = max(title_height - line_spacing, 40)
    
    # Header: 60px, Footer: 50px, Padding/Spacing: 100px
    card_height = 60 + title_height + 50 + (padding * 2) + 20
    
    # ── Draw Card ────────────────────────────────────────────
    # Transparent canvas
    canvas = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Colors
    bg_color = (26, 26, 27, 240)        # Reddit Dark Mode Background (#1A1A1B, 94% opaque)
    reddit_orange = (255, 69, 0, 255)   # #FF4500
    text_white = (255, 255, 255, 255)   # #FFFFFF
    text_gray = (120, 124, 126, 255)    # #787C7E
    border_gray = (52, 53, 54, 255)     # #343536
    
    # Draw rounded background
    draw.rounded_rectangle(
        [(0, 0), (card_width, card_height)],
        radius=20,
        fill=bg_color,
        outline=border_gray,
        width=2
    )
    
    # 1. Header (Subreddit Badge, Subreddit Name, Author, Timestamp)
    y_cursor = padding
    
    if config.OVERLAY_PROFILE_ICON:
        # Draw circular orange badge placeholder
        badge_radius = 20
        badge_center = (padding + badge_radius, y_cursor + badge_radius)
        draw.ellipse(
            [(badge_center[0] - badge_radius, badge_center[1] - badge_radius),
             (badge_center[0] + badge_radius, badge_center[1] + badge_radius)],
            fill=reddit_orange
        )
        # Draw small 'r/' text on badge
        draw.text(
            (badge_center[0] - 8, badge_center[1] - 12),
            "r",
            font=font_meta_bold,
            fill=text_white
        )
        x_cursor = padding + (badge_radius * 2) + 15
    else:
        x_cursor = padding
        
    # Subreddit Name
    sub_tag = f"r/{post.subreddit}" if config.OVERLAY_SUBREDDIT_TAG else "r/Reddit"
    draw.text((x_cursor, y_cursor + 6), sub_tag, font=font_meta_bold, fill=text_white)
    
    # Get width of subreddit tag to align u/author
    sub_bbox = draw.textbbox((0, 0), sub_tag, font=font_meta_bold)
    sub_w = sub_bbox[2] - sub_bbox[0]
    
    # Author and Meta info
    meta_text = f" • Posted by u/{post.author}"
    draw.text(
        (x_cursor + sub_w + 5, y_cursor + 6),
        meta_text,
        font=font_meta,
        fill=text_gray
    )
    
    y_cursor += 65  # Advance below header
    
    # 2. Post Title
    for line in wrapped_title:
        draw.text((padding, y_cursor), line, font=font_title, fill=text_white)
        # Compute height of line
        bbox = draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        y_cursor += h + line_spacing
        
    y_cursor += 15  # Spacing before footer
    
    # Draw simple thin separator line
    draw.line(
        [(padding, y_cursor), (card_width - padding, y_cursor)],
        fill=border_gray,
        width=1
    )
    y_cursor += 15
    
    # 3. Footer (Upvotes & Comments counts)
    # Formats count like 1.2k if > 1000
    def format_count(num: int) -> str:
        if num >= 1000:
            return f"{num / 1000:.1f}k"
        return str(num)
        
    stats_text = f"▲ {format_count(post.score)}  |  💬 {format_count(post.num_comments)} Comments"
    draw.text((padding, y_cursor), stats_text, font=font_meta_bold, fill=text_gray)
    
    # Save the card image
    canvas.save(output_path, "PNG")
    logger.info(f"Reddit card overlay generated at {output_path} ({card_width}x{card_height})")
    return output_path
