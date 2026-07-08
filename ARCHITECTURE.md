# Architectural Design: Reddit to Shorts Pipeline

This document details the software architecture of the Reddit-to-Shorts content pipeline. The system is designed to be highly modular, testable, and robust against network, API, and rendering failures.

---

## 🏗 Component Diagram

```mermaid
flowchart TD
    %% Component Layers
    subgraph Ingestion["1. Ingestion Layer"]
        crawler["Reddit Crawler (src/reddit/client.py)"]
        reddit_json["Anonymous JSON Feed"]
        reddit_praw["PRAW API Client"]
        dedup_db[("Processed Posts DB (data/database/processed_posts.json)")]
    end

    subgraph LLM["2. Narration Layer"]
        llm_factory["LLM Factory (src/narration/__init__.py)"]
        groq["Groq Client"]
        openai["OpenAI / DeepSeek / OpenRouter"]
        gemini["Gemini Client"]
        ollama["Ollama Client"]
        fallback_script["Local Regex Cleanup (Fallback)"]
    end

    subgraph Audio["3. Voice Layer (TTS)"]
        tts_factory["TTS Factory (src/voice/__init__.py)"]
        edge["Edge TTS (Free)"]
        eleven["ElevenLabs API"]
        oai_tts["OpenAI TTS"]
        aligner["Character-Duration Aligner (src/voice/helpers.py)"]
    end

    subgraph Video["4. Compositing Layer"]
        bg_mgr["Background Manager (src/video/background.py)"]
        overlay_draw["Reddit Card Drawer (src/video/overlay.py)"]
        ffmpeg_comp["Video Renderer (src/video/renderer.py)"]
        ass_gen["Kinetic Subtitle Generator (ASS)"]
    end

    subgraph Upload["5. Distribution Layer"]
        yt_upload["YouTube Upload Manager (src/upload/youtube.py)"]
        schedule_chk["Scheduler Checker (src/upload/scheduler.py)"]
        upload_db[("Upload History DB (data/database/upload_history.json)")]
    end

    %% Data Flow Connections
    subgraph Trigger["0. Scheduling Trigger"]
        cron["Cron / GitHub Actions / Task Scheduler"]
    end

    cron -->|Check schedule| schedule_chk
    schedule_chk -->|Query limit & slot| upload_db
    schedule_chk -->|Run permitted| crawler

    crawler -->|1. Fetch posts| reddit_json & reddit_praw
    crawler -->|2. Check duplicates| dedup_db
    crawler -->|3. Emit Post| llm_factory

    llm_factory -->|4. Request Script| groq & openai & gemini & ollama
    llm_factory -.->|LLM Fail Fallback| fallback_script
    llm_factory -->|5. Emit Narration & Accent Words| tts_factory

    tts_factory -->|6. Generate Audio| edge & eleven & oai_tts
    eleven & oai_tts -->|7. Estimate word timings| aligner
    tts_factory -->|8. Emit Audio & Timing Data| ffmpeg_comp

    bg_mgr -->|9. Fetch clip (LFU Selection)| ffmpeg_comp
    overlay_draw -->|10. Draw Card PNG| ffmpeg_comp
    ffmpeg_comp -->|11. Generate ASS| ass_gen
    ffmpeg_comp -->|12. Compositing via FFmpeg| yt_upload

    yt_upload -->|13. Upload Short (OAuth)| upload_db
```

---

## 📂 Directory Layout

The application has been restructured from single-file scripts into a modular Python package:

```text
Brain_Bot/
│
├── config.py                 # Pydantic-like Central Configuration Manager
├── run_pipeline.py           # Core Master Pipeline Orchestrator (CLI Entry Point)
├── get_refresh_token.py      # OAuth Helper tool to fetch YT Refresh Tokens
├── requirements.txt          # Pip dependencies list
│
├── src/                      # Source Code Package
│   ├── __init__.py           # Package Initializer
│   ├── logger.py             # Structured Rotational Telemetry Logger
│   │
│   ├── reddit/               # Reddit Crawling & Verification Submodule
│   │   ├── __init__.py
│   │   ├── models.py         # Structured RedditPost Dataclass
│   │   └── client.py         # Ingestion, Validation filters & Deduplication DB
│   │
│   ├── narration/            # LLM Narration Scripting Submodule
│   │   ├── __init__.py       # Provider Factory & Local Fallback cleanups
│   │   ├── base.py           # LLM Base Abstract Client Interface
│   │   ├── groq.py           # Groq Client wrapper
│   │   ├── gemini.py         # Gemini Client wrapper
│   │   ├── openai_like.py    # OpenAI, DeepSeek, OpenRouter & Ollama client wrapper
│   │   ├── prompts.py        # System Prompt templates for commentary / verbatim modes
│   │   └── helpers.py        # Script parsing, emoji & markdown stripping, emphasis tagger
│   │
│   ├── voice/                # Text-to-Speech Submodule
│   │   ├── __init__.py       # TTS Factory & Edge-TTS Fallback orchestration
│   │   ├── base.py           # Abstract Base Class for TTS engines
│   │   ├── edge.py           # Microsoft Edge TTS Client (sentence timing streams)
│   │   ├── elevenlabs.py     # ElevenLabs REST Client
│   │   ├── openai_tts.py     # OpenAI Speech REST Client
│   │   └── helpers.py        # Character-Duration alignment for REST providers
│   │
│   └── video/                # Video Compositing Submodule
│   │   ├── __init__.py       # Exposes selection, overlay drawing, and FFmpeg renderers
│   │   ├── background.py     # yt-dlp downloader, FFmpeg scene cutter, LFU clip picker
│   │   ├── overlay.py        # Pill-based high-res Reddit card image generator
│   │   └── renderer.py       # compositing filter graph (blurs, card, progress bars, subtitles)
│   │
│   └── upload/               # Distribution & Scheduler Submodule
│       ├── __init__.py
│       ├── youtube.py        # Chunked resumable YouTube uploads & daily quota tracking
│       └── scheduler.py      # State-based time window slot parser
│
└── data/                     # Persistent App Data Directory
    ├── raw/                  # Temp storage for raw downloads
    ├── output/               # Rendered final shorts and subtitle assets
    ├── clips/                # Pre-sliced background video segments
    ├── cache/                # yt-dlp download logs & YouTube OAuth token cache
    └── database/             # App State Databases
        ├── processed_posts.json   # Crawled posts history (prevents duplicates)
        ├── used_backgrounds.json  # Least-Frequently-Used background counts
        └── upload_history.json    # YouTube uploaded IDs & daily limit tracker
```

---

## 🛡️ Fault Tolerance & Survivability

To satisfy production requirements, the pipeline implements multi-layered error recovery:

1. **Stateful Scheduling**: Instead of daemon loops, the scheduler (`check_scheduler_run`) matches slot windows against actual successful upload logs in `upload_history.json`. This makes it completely self-healing across power outages or CI job delays.
2. **Reddit API Dual Ingestion**: If PRAW credentials are omitted or API quotas are hit, the client falls back to anonymous `.json` crawling.
3. **LLM Parser Resiliency**: If LLMs return empty strings, invalid blocks, or fail due to timeouts, a local script cleaner parses the post directly using regex to output clean narration.
4. **TTS Engine Fallback**: If ElevenLabs or OpenAI TTS is down or out of credits, synthesis falls back to Microsoft Edge TTS (free, no key required).
5. **YouTube Upload Retries**: The OAuth uploader splits video uploads into chunks and retries chunks up to 3 times with exponential backoff on transport errors.

---

## 🎨 Subtitle & Compositing Filter Graph

The rendering system executes a sophisticated single-pass FFmpeg command to maximize speed and quality:

1. **Aspect Ratio Crop**: Scale the landscape background clip to fill vertical space while maintaining center focus:
   `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`
2. **Reddit Card Overlay**: Blends the card PNG generated by Pillow in the center:
   `[v_base][2:v]overlay=x=(1080-w)/2:y=300[v_card]`
3. **Word-Popping Captions**: Burns Advanced SubStation Alpha (`captions.ass`) subtitles into the video. Timing files use custom pop tags:
   `{\c<color>\an5\fscx125\fscy125\t(0,100,\fscx100,\fscy100)}word`
   This instantly inflates each word by 25% and shrinks it to 100% over 100ms as it is spoken.
4. **Animated Progress Bar**: Draws a thin colored box at the bottom, dynamically mapping width to elapsed playback time:
   `drawbox=x=0:y=1880:w='1080*t/<duration>':h=12:color=0xFF5500@0.9:t=fill`