import asyncio
import subprocess
from pathlib import Path
from typing import Tuple, List

import config
from src.logger import logger
from src.voice.base import BaseVoiceProvider, SentenceTiming

# Timeout settings
TTS_TIMEOUT = 120
FFPROBE_TIMEOUT = 30


def _ffprobe_duration(path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
            timeout=FFPROBE_TIMEOUT,
        ).strip()
        return float(out)
    except Exception as e:
        logger.error(f"ffprobe failed to read audio duration: {e}")
        return 0.0


async def _synthesize_with_timing(
    text: str,
    out_path: Path,
    voice: str,
) -> List[SentenceTiming]:
    """Synthesize speech with sentence-level timestamps using edge-tts."""
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    sentences: List[SentenceTiming] = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                sentences.append(
                    SentenceTiming(
                        text=chunk["text"],
                        offset_ms=int(chunk["offset"]) // 10_000,
                        duration_ms=int(chunk["duration"]) // 10_000,
                    )
                )

    return sentences


class EdgeVoiceProvider(BaseVoiceProvider):
    """Microsoft Edge TTS Voice Provider."""

    def synthesize(
        self, 
        text: str, 
        output_path: Path, 
        voice: str | None = None
    ) -> Tuple[float, List[SentenceTiming]]:
        voice = voice or config.TTS_VOICE or "en-US-AndrewNeural"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Synthesizing voiceover with Edge TTS (voice: {voice})")
        try:
            sentences = asyncio.run(
                asyncio.wait_for(
                    _synthesize_with_timing(text, output_path, voice),
                    timeout=TTS_TIMEOUT,
                )
            )
        except asyncio.TimeoutError:
            logger.error(f"Edge TTS timed out after {TTS_TIMEOUT}s")
            # If partial audio was written, attempt to use it, otherwise raise
            if output_path.exists() and output_path.stat().st_size > 1000:
                logger.warning("Partial audio file found, using it.")
                sentences = []
            else:
                raise TimeoutError("TTS synthesis timed out and no audio was produced.")
        except Exception as e:
            logger.error(f"Edge TTS synthesis error: {e}")
            raise e

        duration = _ffprobe_duration(output_path)
        logger.info(f"Generated Edge TTS voiceover: {duration:.2f}s ({len(sentences)} sentences)")
        return duration, sentences
