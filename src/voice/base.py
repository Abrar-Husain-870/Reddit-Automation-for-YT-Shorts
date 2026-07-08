from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List, TypedDict

class SentenceTiming(TypedDict):
    text: str
    offset_ms: int
    duration_ms: int


class BaseVoiceProvider(ABC):
    """Abstract Base Class for Voice Synthesis (TTS) Providers."""

    @abstractmethod
    def synthesize(
        self, 
        text: str, 
        output_path: Path, 
        voice: str | None = None
    ) -> Tuple[float, List[SentenceTiming]]:
        """
        Synthesize speech from text and save to output_path.
        
        Args:
            text: The plain text to speak.
            output_path: Path to output MP3/WAV file.
            voice: Optional voice ID/name to override default config.
            
        Returns:
            Tuple of (total_duration_seconds, list_of_sentence_timings)
        """
        pass
