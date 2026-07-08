from typing import Tuple, List

import config
from src.logger import logger
from src.narration.base import BaseLLMProvider
from src.narration.helpers import strip_markdown, strip_emojis, extract_emphasis_from_text
from src.reddit.models import RedditPost


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to instantiate the configured LLM provider."""
    provider_name = config.LLM_PROVIDER.lower()
    
    if provider_name == "groq":
        from src.narration.groq import GroqProvider
        return GroqProvider()
    elif provider_name in ("openai", "deepseek", "openrouter", "ollama"):
        from src.narration.openai_like import OpenAILikeProvider
        return OpenAILikeProvider()
    elif provider_name == "gemini":
        from src.narration.gemini import GeminiProvider
        return GeminiProvider()
    else:
        logger.warning(f"Unknown LLM provider '{config.LLM_PROVIDER}'. Defaulting to Groq.")
        from src.narration.groq import GroqProvider
        return GroqProvider()


def generate_script_with_fallback(
    post: RedditPost, 
    mode: str = None, 
    style: str = None
) -> Tuple[str, str, List[str]]:
    """
    Generate narration script from a Reddit post.
    Falls back to a clean reading of the post if the LLM provider fails.
    
    Returns:
        Tuple of (narration, title, emphasis_words)
    """
    mode = mode or config.NARRATION_MODE
    style = style or config.CAPTION_STYLE
    
    try:
        provider = get_llm_provider()
        narration, title, emphasis = provider.generate_narration(post, mode, style)
        
        # Verify result is valid
        if narration and len(narration.split()) >= 15:
            return narration, title, emphasis
        else:
            raise ValueError("Generated script is too short or empty")
            
    except Exception as e:
        logger.warning(f"LLM script generation failed ({e}). Using local regex cleanup fallback.")
        
        # Local fallback: read the post naturally by cleaning it up
        clean_title = strip_markdown(strip_emojis(post.title))
        clean_body = strip_markdown(strip_emojis(post.selftext))
        
        # Truncate content to fit 45-90 seconds (approx 120-150 words)
        words = f"{clean_title}. {clean_body}".split()
        if len(words) > 180:
            narration = " ".join(words[:180]) + "..."
        else:
            narration = " ".join(words)
            
        title = clean_title[:55]
        emphasis = extract_emphasis_from_text(narration, limit=4)
        
        logger.info("Local fallback narration generated successfully")
        return narration, title, emphasis
