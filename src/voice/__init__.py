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
    Tries configured provider, then Edge TTS, then OpenAI TTS, then gTTS fallback.
    """
    if output_path is None:
        output_path = config.OUTPUT_DIR / "voiceover.mp3"
        
    # 1. Try configured provider
    try:
        provider = get_voice_provider()
        duration, timings = provider.synthesize(text, output_path, voice)
        return duration, timings
    except Exception as e:
        logger.warning(f"Configured TTS provider '{config.TTS_PROVIDER}' failed: {e}")

    # 2. Try Edge TTS if configured wasn't Edge
    if config.TTS_PROVIDER.lower() != "edge":
        try:
            logger.info("Attempting Edge TTS fallback...")
            from src.voice.edge import EdgeVoiceProvider
            fallback_provider = EdgeVoiceProvider()
            return fallback_provider.synthesize(text, output_path, "en-US-AndrewNeural")
        except Exception as ee:
            logger.warning(f"Edge TTS fallback failed: {ee}")

    # 3. Try OpenAI TTS if configured with API key
    if config.OPENAI_API_KEY and config.TTS_PROVIDER.lower() != "openai":
        try:
            logger.info("Attempting OpenAI TTS fallback...")
            from src.voice.openai_tts import OpenAITTSVoiceProvider
            return OpenAITTSVoiceProvider().synthesize(text, output_path, "onyx")
        except Exception as oe:
            logger.warning(f"OpenAI TTS fallback failed: {oe}")

    # 4. Try gTTS as guaranteed zero-cost fallback
    try:
        logger.info("Attempting gTTS fallback...")
        from src.voice.gtts_voice import GTTSVoiceProvider
        return GTTSVoiceProvider().synthesize(text, output_path)
    except Exception as ge:
        logger.error(f"All TTS providers including gTTS failed: {ge}")
        raise ge
