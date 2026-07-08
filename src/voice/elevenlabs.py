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


class ElevenLabsVoiceProvider(BaseVoiceProvider):
    """ElevenLabs TTS Provider using REST API."""

    def __init__(self) -> None:
        self.api_key = config.ELEVENLABS_API_KEY
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY is not configured. ElevenLabsVoiceProvider will fail.")

    def synthesize(
        self, 
        text: str, 
        output_path: Path, 
        voice: str | None = None
    ) -> Tuple[float, List[SentenceTiming]]:
        voice_id = voice or config.TTS_VOICE or config.ELEVENLABS_VOICE_ID
        if not self.api_key:
            raise ValueError("ElevenLabs API Key is not configured.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "audio/mpeg"
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        logger.info(f"Synthesizing voiceover with ElevenLabs (voice: {voice_id})")
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
            logger.error(f"ElevenLabs HTTP Error {e.code}: {err_msg}")
            raise Exception(f"ElevenLabs API failed: {err_msg}")
        except Exception as e:
            logger.error(f"ElevenLabs synthesis request failed: {e}")
            raise e
            
        duration = _ffprobe_duration(output_path)
        sentences = approximate_sentence_timings(text, duration)
        return duration, sentences
