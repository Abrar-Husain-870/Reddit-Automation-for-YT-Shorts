from pathlib import Path
from typing import Tuple, List

import config
from src.logger import logger
from src.voice.base import BaseVoiceProvider, SentenceTiming


def get_voice_provider() -> BaseVoiceProvider:
    """Factory function to instantiate the configured TTS provider."""
    provider_name = config.TTS_PROVIDER.lower()
    
    if provider_name == "edge":
        from src.voice.edge import EdgeVoiceProvider
        return EdgeVoiceProvider()
    elif provider_name == "elevenlabs":
        from src.voice.elevenlabs import ElevenLabsVoiceProvider
        return ElevenLabsVoiceProvider()
    elif provider_name == "openai":
        from src.voice.openai_tts import OpenAITTSVoiceProvider
        return OpenAITTSVoiceProvider()
    else:
        logger.warning(f"Unknown/unsupported voice provider '{config.TTS_PROVIDER}'. Defaulting to Edge.")
        from src.voice.edge import EdgeVoiceProvider
        return EdgeVoiceProvider()


def synthesize_voiceover_with_fallback(
    text: str, 
    output_path: Path | None = None, 
    voice: str | None = None
) -> Tuple[float, List[SentenceTiming]]:
    """
    Synthesize voiceover from text, saving to output_path.
    If the configured provider fails, falls back to Edge TTS.
    """
    if output_path is None:
        output_path = config.OUTPUT_DIR / "voiceover.mp3"
        
    try:
        provider = get_voice_provider()
        duration, timings = provider.synthesize(text, output_path, voice)
        return duration, timings
    except Exception as e:
        logger.warning(f"Configured TTS provider '{config.TTS_PROVIDER}' failed: {e}. Falling back to Edge TTS.")
        
        # Override config settings temporarily for fallback
        from src.voice.edge import EdgeVoiceProvider
        fallback_provider = EdgeVoiceProvider()
        fallback_voice = "en-US-AndrewNeural"
        
        try:
            duration, timings = fallback_provider.synthesize(text, output_path, fallback_voice)
            return duration, timings
        except Exception as fe:
            logger.error(f"Fallback Edge TTS also failed: {fe}")
            raise fe
