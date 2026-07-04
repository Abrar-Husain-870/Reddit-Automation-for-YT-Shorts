# GTA VI Brainrot Shorts Automation Pipeline

Fully automated pipeline to:
1. Download GTA VI gameplay clips from YouTube
2. Split into short segments via scene detection
3. Generate brainrot-style scripts via Groq LLM (free)
4. Synthesize voiceover via Edge TTS (free)
5. Overlay word-by-word captions (brainrot style)
6. Render 9:16 vertical MP4
7. Upload to YouTube Shorts + Instagram Reels

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq LLM API key |
| `YT_CLIENT_ID` | For YouTube | OAuth client ID |
| `YT_CLIENT_SECRET_VALUE` | For YouTube | OAuth client secret |
| `YT_REFRESH_TOKEN` | For YouTube | YouTube refresh token |
| `IG_USERNAME` | For Instagram | Instagram login |
| `IG_PASSWORD` | For Instagram | Instagram password |

## Usage

**Full pipeline (one-shot):**
```bash
python run_pipeline.py
```

**Individual steps:**
```bash
python download_clips.py           # Download fresh GTA VI gameplay
python process_clips.py            # Split into short clips
python generate_script.py          # Generate brainrot scripts
python generate_voiceover.py       # TTS audio
python render_short.py             # Render final video with captions
python upload_youtube.py           # Upload to YouTube Shorts
```

**Daily automation (GitHub Actions ready):**
The pipeline is designed to run via cron — set up a scheduled workflow similar to the existing YouTube bot.