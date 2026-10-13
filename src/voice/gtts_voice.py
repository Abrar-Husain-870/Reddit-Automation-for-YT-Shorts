from pathlib import Path
from typing import Tuple, List

from src.logger import logger
from src.voice.base import BaseVoiceProvider, SentenceTiming
from src.voice.edge import _ffprobe_duration
from src.voice.helpers import approximate_sentence_timings


class GTTSVoiceProvider(BaseVoiceProvider):
    """Google Translate TTS Provider (Free, reliable fallback)."""

    def synthesize(
        self, 
        text: str, 
        output_path: Path, 
        voice: str | None = None
    ) -> Tuple[float, List[SentenceTiming]]:
        from gtts import gTTS

        logger.info("Synthesizing voiceover with gTTS fallback...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        tts = gTTS(text=text, lang="en", tld="com")
        tts.save(str(output_path))
        
        duration = _ffprobe_duration(output_path)
        sentences = approximate_sentence_timings(text, duration)
        logger.info(f"Generated gTTS voiceover: {duration:.2f}s ({len(sentences)} sentences)")
        return duration, sentences
