import re
from typing import List
from src.voice.base import SentenceTiming

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using basic punctuation boundaries."""
    # Match sentences ending with period, exclamation, question mark, or colon
    sentence_end = re.compile(r'(?<=[.!?])\s+')
    raw_sentences = sentence_end.split(text)
    
    sentences = []
    for s in raw_sentences:
        s_clean = s.strip()
        if s_clean:
            sentences.append(s_clean)
            
    # If no sentences found, return the text itself as a single sentence
    if not sentences:
        return [text]
    return sentences


def approximate_sentence_timings(text: str, total_duration_seconds: float) -> List[SentenceTiming]:
    """
    Split text into sentences and approximate timestamps based on character length.
    Useful for TTS providers that do not natively provide word/sentence timings.
    """
    sentences = split_into_sentences(text)
    total_chars = sum(len(s) for s in sentences)
    
    if total_chars == 0:
        return []
        
    timings: List[SentenceTiming] = []
    current_ms = 0
    total_ms = int(total_duration_seconds * 1000)
    
    for i, s in enumerate(sentences):
        # Calculate duration proportional to character length
        pct = len(s) / total_chars
        duration_ms = int(total_ms * pct)
        
        # Ensure we don't exceed total_ms due to rounding errors
        if i == len(sentences) - 1:
            duration_ms = max(0, total_ms - current_ms)
            
        timings.append(
            SentenceTiming(
                text=s,
                offset_ms=current_ms,
                duration_ms=duration_ms
            )
        )
        current_ms += duration_ms
        
    return timings
