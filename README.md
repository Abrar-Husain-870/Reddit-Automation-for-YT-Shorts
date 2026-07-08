# Reddit to YouTube Shorts / Reels Automation System

A fully automated, modular Python pipeline that crawls posts from subreddits, generates AI scripts, synthesizes voiceovers, and renders high-quality 9:16 vertical Shorts at 60 FPS with word-popping captions and post screenshot overlays, then uploads them to YouTube.

## 🚀 Features

- **Reddit Ingestion**: Crawls subreddits (e.g., `r/AskReddit`, `r/tifu`), applies NSFW, score, comment, and length filters, and stores post IDs permanently in a JSON database to prevent duplicate videos.
- **Interchangeable AI Narrators**: Supports Mode 1 (Verbatim/Natural reading) and Mode 2 (Engaging commentary/story hooks). Abstracted client supports **Groq**, **DeepSeek**, **Gemini**, **OpenAI**, **OpenRouter**, and local **Ollama** endpoints out-of-the-box.
- **Modular Voice Synthesis**: Supports **Edge TTS** (free, default), **ElevenLabs**, and **OpenAI TTS** with automatic character-based alignment or native timestamps.
- **Advanced Video Composer**: Slices 60 FPS background videos (Minecraft parkour, Subway Surfers, satisfying videos), overlays a PIL-generated dark mode Reddit post card, burns bouncy word-highlighting captions (ASS subtitles), and adds an animated progress bar.
- **YouTube Upload Gatekeeper**: Automates uploads via OAuth2 refresh tokens, tracks uploads, and limits runs to a maximum of 4 uploads per day to prevent channel bans.
- **Scheduling**: Designed to work seamlessly with cron, Windows Task Scheduler, GitHub Actions, or Docker.

---

## 🛠 Setup

### Prerequisites
- Python 3.12 or 3.13
- **FFmpeg** (installed and added to your system's PATH)

### Installation
1. Clone the repository and navigate to the folder.
2. Initialize virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and fill in your keys and preferences.

### Key Config Options (in `.env`)
| Variable | Default / Example | Description |
|---|---|---|
| `SUBREDDITS` | `AskReddit, tifu, Unexpected` | Comma-separated target subreddits |
| `REDDIT_SORT` | `top` | Post sorting (`top`, `hot`, `rising`, `new`) |
| `NARRATION_MODE` | `commentary` | Script style (`natural` or `commentary`) |
| `LLM_PROVIDER` | `groq` | Provider (`groq`, `gemini`, `openai`, `deepseek`, `openrouter`, `ollama`) |
| `LLM_MODEL` | `llama-3.1-8b-instant` | Model name corresponding to LLM provider |
| `TTS_PROVIDER` | `edge` | Voice synthesiser (`edge`, `elevenlabs`, `openai`) |
| `BACKGROUND_PROVIDERS`| `minecraft parkour gameplay 1080p` | Search terms for downloading background clips |
| `MAX_VIDEOS_PER_DAY` | `4` | Limit on successful daily uploads |
| `UPLOAD_SCHEDULE_TIMES` | `09:00, 13:00, 17:00, 21:00` | Scheduled windows for cron runs |

---

## 🎮 Usage

### Run End-to-End Pipeline
Execute the full pipeline with a single command:
```bash
python run_pipeline.py
```

### Command Line Overrides
- **Bypass Scheduler**: Force run immediately regardless of scheduled hours:
  ```bash
  python run_pipeline.py --force
  ```
- **Skip YouTube Upload**: Generate and render video locally without uploading:
  ```bash
  python run_pipeline.py --no-upload
  ```
- **Target a Subreddit**: Fetch only from a specific subreddit for this run:
  ```bash
  python run_pipeline.py --subreddit AskReddit
  ```
- **Style Captions**: Choose styling preset (`chaotic` [orange], `meme` [green], `story` [white], `npc` [purple]):
  ```bash
  python run_pipeline.py --style meme
  ```
- **Skip Downloader**: Skip YouTube background downloads and use pre-existing local clips:
  ```bash
  python run_pipeline.py --skip-download
  ```

### Helper Scripts
Generate a YouTube OAuth refresh token locally:
```bash
python get_refresh_token.py
```
This opens a local server to auth with Google and prints a token to paste into your `.env` file under `YT_REFRESH_TOKEN`.