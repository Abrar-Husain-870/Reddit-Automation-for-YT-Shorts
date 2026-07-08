import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict

import config
from src.logger import logger

RENDER_TIMEOUT = 600
FFPROBE_TIMEOUT = 60

# Palette color schemes (ASS colors are in format &HAAABBBCC, where AA is alpha, BB is blue, GG is green, RR is red)
STYLE_PALETTES = {
    "chaotic": ["&H000045FF", "&H004763FF", "&H000000FF", "&H0000A5FF",
                "&H000045FF", "&H004763FF", "&H000000FF", "&H0000A5FF"],  # Orange/Red/Yellows (reversed BB/GG/RR for ASS)
    "meme":   ["&H0000FF00", "&H0032CD32", "&H002FDFFF", "&H0000FF7F",
               "&H0000FF00", "&H0032CD32", "&H002FDFFF", "&H0000FF7F"],  # Greens
    "story":  ["&H00FFFFFF", "&H00FFF8F0", "&H00E0E0E0", "&H00D3D3D3",
               "&H00FFFFFF", "&H00FFF8F0", "&H00E0E0E0", "&H00D3D3D3"],  # Whites/Silvers
    "npc":    ["&H00DC7F93", "&H00E22B8A", "&H00D355BA", "&H00D670DA",
               "&H00DC7F93", "&H00E22B8A", "&H00D355BA", "&H00D670DA"],  # Purples/Pinks
}

ALTERNATE_Y = [1350, 1500, 1650, 1400, 1550, 1700]


def _get_audio_duration(path: Path) -> float:
    """Get duration of audio file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", 
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", 
        str(path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT)
    return float(r.stdout.strip())


def _build_word_timings(
    words: List[str], 
    audio_dur: float,
    sentence_timings: List[dict] | None = None
) -> List[Tuple[float, float, str]]:
    """Map words to timestamps using sentence boundaries for alignment."""
    result = []
    n = len(words)

    if sentence_timings and len(sentence_timings) > 0:
        word_idx = 0
        for sent in sentence_timings:
            s_text = sent.get("text", "")
            s_start = sent.get("offset_ms", 0) / 1000
            s_dur = sent.get("duration_ms", 1000) / 1000
            s_end = s_start + s_dur
            s_words = [w for w in s_text.split() if w.strip()]
            n_s_words = len(s_words)
            
            if n_s_words > 0 and word_idx < n:
                w_per = s_dur / n_s_words
                for j in range(n_s_words):
                    if word_idx >= n:
                        break
                    ws = s_start + j * w_per
                    we = min(ws + w_per, s_end)
                    result.append((ws, we, words[word_idx]))
                    word_idx += 1
                    
        # Allocate any leftover words to the end of the audio
        remaining = n - word_idx
        if remaining > 0:
            last_end = result[-1][1] if result else 0.0
            time_left = max(0.1, audio_dur - last_end)
            w_per = time_left / max(remaining, 1)
            for j in range(remaining):
                ws = last_end + j * w_per
                we = min(ws + w_per, audio_dur)
                result.append((ws, we, words[word_idx]))
                word_idx += 1
    else:
        # Uniform fallback mapping
        w_per = audio_dur / max(n, 1)
        for i, w in enumerate(words):
            ws = i * w_per
            we = min((i + 1) * w_per, audio_dur)
            result.append((ws, we, w))
            
    return result


def _build_ass_subtitles(
    timings: List[Tuple[float, float, str]],
    style: str = "chaotic",
    emphasis_words: List[str] | None = None
) -> str:
    """Build ASS formatted subtitle content with word popping effects."""
    palette = STYLE_PALETTES.get(style, STYLE_PALETTES["chaotic"])
    emphasis_set = set(w.upper() for w in (emphasis_words or []))

    # Font sizes: 90pt normal, 130pt emphasis (1.5x)
    ass = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Emphasis,{config.CAPTION_FONT},130,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,4,5,0,0,0,1\n"
        f"Style: Normal,{config.CAPTION_FONT},90,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,4,5,0,0,0,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    def _t(s):
        h = int(s // 3600)
        m = int((s % 3600) // 60)
        return f"{h}:{m:02d}:{s % 60:05.2f}"

    for i, (ts, te, w) in enumerate(timings):
        word_clean = w.strip(".,!?;:\"'()[]{}*-").upper()
        is_emphasis = word_clean in emphasis_set
        style_name = "Emphasis" if is_emphasis else "Normal"
        color = palette[i % len(palette)]
        alt_idx = i % len(ALTERNATE_Y)
        y_margin = ALTERNATE_Y[alt_idx]
        
        # Word popping animation: start 1.25x larger and scale down to 1x over 100ms
        pop_effect = "\\fscx125\\fscy125\\t(0,100,\\fscx100,\\fscy100)"
        
        ass += f"Dialogue: 0,{_t(ts)},{_t(te)},{style_name},,0,0,{y_margin},,{{\\c{color}\\an5{pop_effect}}}{w}\n"

    return ass


def render_short(
    clip_path: Path,
    audio_path: Path,
    narration: str,
    overlay_card_path: Path | None = None,
    output_path: Path | None = None,
    sentence_timings: List[dict] | None = None,
    style: str = "chaotic",
    emphasis_words: List[str] | None = None
) -> Path:
    """Render a fully customized 9:16 vertical Short at 60 FPS."""
    if output_path is None:
        output_path = config.OUTPUT_DIR / "final_short.mp4"
        
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get audio duration to sync video cut length
    audio_dur = _get_audio_duration(audio_path)
    logger.info(f"Rendering pipeline: Background '{clip_path.name}' | Audio duration: {audio_dur:.2f}s")
    
    # Clean narration string
    clean_narration = narration.replace("**", "").replace("__", "").replace("*", "")
    clean_narration = re.sub(r'[^\w\s\'",.!?;:\-]', "", clean_narration).strip()
    words = [w for w in clean_narration.split() if w.strip()]
    
    # Map timestamps and build subtitle ASS file
    timings = _build_word_timings(words, audio_dur, sentence_timings)
    ass_content = _build_ass_subtitles(timings, style, emphasis_words)
    
    # Save ASS captions
    ass_path = config.OUTPUT_DIR / "captions.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    
    # To fix Windows path issues with FFmpeg subtitles filter:
    # Use relative path prefix or escape backslashes
    ass_safe_path = "data/output/captions.ass"
    
    # Assemble inputs
    inputs = [
        "-i", str(clip_path),
        "-i", str(audio_path)
    ]
    
    # Filter Complex Building
    filter_chains = []
    
    # 1. Base background scaling and formatting
    if config.OVERLAY_BACKGROUND_BLUR:
        # Create a blurred background layer, scale foreground over it
        filter_chains.append(
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bg]"
        )
        filter_chains.append(
            "[0:v]scale=1080:-1[fg_scaled]"
        )
        filter_chains.append(
            "[bg][fg_scaled]overlay=x=0:y=(1920-h)/2[v_base]"
        )
    else:
        # Standard scale and crop to 9:16
        filter_chains.append(
            "[0:v]scale=1080:1920:flags=lanczos:force_original_aspect_ratio=increase,crop=1080:1920,unsharp=5:5:1.0:5:5:0.0[v_base]"
        )
        
    last_v_tag = "v_base"
    
    # 2. Add Reddit card overlay if provided
    if config.OVERLAY_REDDIT_SCREENSHOT and overlay_card_path and overlay_card_path.exists():
        inputs.extend(["-i", str(overlay_card_path)])
        # overlay is card (input index 2)
        # Position card in upper middle (y=300)
        filter_chains.append(
            f"[{last_v_tag}][2:v]overlay=x=(1080-w)/2:y=300[v_card]"
        )
        last_v_tag = "v_card"
        
    # 3. Add captions
    filter_chains.append(
        f"[{last_v_tag}]subtitles={ass_safe_path}[v_sub]"
    )
    last_v_tag = "v_sub"
    
    # 4. Optional Progress Bar (Draw box dynamically changing width)
    if config.OVERLAY_PROGRESS_BAR:
        progress_color = "0xFF5500"  # Orange
        bar_y = 1880
        bar_height = 12
        filter_chains.append(
            f"[{last_v_tag}]drawbox=x=0:y={bar_y}:w='1080*t/{audio_dur:.2f}':h={bar_height}:color={progress_color}@0.9:t=fill[v_final]"
        )
        last_v_tag = "v_final"
        
    filter_complex_str = ";".join(filter_chains)
    
    # Build complete FFmpeg command
    cmd = [
        "ffmpeg", "-y"
    ]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex_str,
        "-map", f"[{last_v_tag}]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-r", str(config.RENDER_FPS),
        "-preset", "medium",
        "-crf", "18",
        "-profile:v", "high",
        "-level", "4.2",
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path)
    ])
    
    logger.info(f"Running FFmpeg render (60 FPS, presets: medium, output: {output_path.name})")
    
    try:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=RENDER_TIMEOUT)
        if r.returncode != 0:
            logger.error(f"FFmpeg failed with exit code {r.returncode}")
            raise RuntimeError(f"FFmpeg render failed with exit code {r.returncode}")
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg render timed out")
        raise TimeoutError("FFmpeg rendering timed out")
        
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✔ Short rendered successfully: {output_path.name} ({size_mb:.2f}MB, 60fps)")
        return output_path
    else:
        raise FileNotFoundError("Rendered video file not found after FFmpeg completion")
