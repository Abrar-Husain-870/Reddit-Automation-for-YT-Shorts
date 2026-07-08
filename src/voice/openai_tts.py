import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Tuple, List

import config
from src.logger import logger
from src.voice.base import BaseVoiceProvider, SentenceTiming
from src.voice.edge import _ffprobe_duration
from src.voice.helpers import approximate_sentence_timings


class OpenAITTSVoiceProvider(BaseVoiceProvider):
    """OpenAI TTS Provider using standard REST API."""

    def __init__(self) -> None:
        self.api_key = config.OPENAI_API_KEY
        if not self.api_key:
            logger.warning("OPENAI_API_KEY is not configured. OpenAITTSVoiceProvider will fail.")

    def synthesize(
        self, 
        text: str, 
        output_path: Path, 
        voice: str | None = None
    ) -> Tuple[float, List[SentenceTiming]]:
        voice_name = voice or config.TTS_VOICE or "onyx"
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not configured.")

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": config.OPENAI_TTS_MODEL,
            "input": text,
            "voice": voice_name
        }
        
        logger.info(f"Synthesizing voiceover with OpenAI TTS (model: {config.OPENAI_TTS_MODEL}, voice: {voice_name})")
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers, 
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.read())
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8") if e else ""
            logger.error(f"OpenAI TTS HTTP Error {e.code}: {err_msg}")
            raise Exception(f"OpenAI TTS API failed: {err_msg}")
        except Exception as e:
            logger.error(f"OpenAI TTS synthesis request failed: {e}")
            raise e
            
        duration = _ffprobe_duration(output_path)
        sentences = approximate_sentence_timings(text, duration)
        return duration, sentences
