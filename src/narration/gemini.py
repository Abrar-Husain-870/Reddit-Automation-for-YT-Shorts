from typing import Tuple, List

import config
from src.logger import logger
from src.narration.base import BaseLLMProvider
from src.narration.helpers import parse_structured_response
from src.narration.prompts import SYSTEM_PROMPT_COMMENTARY, SYSTEM_PROMPT_NATURAL, get_user_prompt
from src.reddit.models import RedditPost


class GeminiProvider(BaseLLMProvider):
    """Gemini LLM provider for script generation."""

    def __init__(self) -> None:
        self.api_key = config.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured. GeminiProvider may fail.")

    def generate_narration(
        self, 
        post: RedditPost, 
        mode: str = "commentary", 
        style: str = "chaotic"
    ) -> Tuple[str, str, List[str]]:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError(
                "The 'google-generativeai' package is required for the Gemini provider. "
                "Please run: pip install google-generativeai"
            )

        if not self.api_key:
            raise ValueError("Gemini client not initialized (missing API key)")

        genai.configure(api_key=self.api_key)
        system_prompt = SYSTEM_PROMPT_COMMENTARY if mode == "commentary" else SYSTEM_PROMPT_NATURAL
        user_prompt = get_user_prompt(post.subreddit, post.title, post.selftext)

        logger.info(f"Sending request to Gemini model: {config.LLM_MODEL}")
        try:
            # Gemini 1.5 system instructions are configured in GenerationConfig
            model = genai.GenerativeModel(
                model_name=config.LLM_MODEL,
                system_instruction=system_prompt
            )
            response = model.generate_content(
                user_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=600,
                )
            )
            
            response_text = response.text
            if not response_text:
                raise ValueError("Received empty response from Gemini")

            parsed = parse_structured_response(response_text, default_title=post.title)
            return parsed["narration"], parsed["title"], parsed["emphasis"]

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise e
