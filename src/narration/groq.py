from typing import Tuple, List

from groq import Groq
import config
from src.logger import logger
from src.narration.base import BaseLLMProvider
from src.narration.helpers import parse_structured_response
from src.narration.prompts import SYSTEM_PROMPT_COMMENTARY, SYSTEM_PROMPT_NATURAL, get_user_prompt
from src.reddit.models import RedditPost


class GroqProvider(BaseLLMProvider):
    """Groq LLM provider for script generation."""

    def __init__(self) -> None:
        self.api_key = config.GROQ_API_KEY
        if not self.api_key:
            logger.warning("GROQ_API_KEY is not configured. GroqProvider may fail.")
        self.client = Groq(api_key=self.api_key) if self.api_key else None

    def generate_narration(
        self, 
        post: RedditPost, 
        mode: str = "commentary", 
        style: str = "chaotic"
    ) -> Tuple[str, str, List[str]]:
        if not self.client:
            raise ValueError("Groq client not initialized (missing API key)")

        system_prompt = SYSTEM_PROMPT_COMMENTARY if mode == "commentary" else SYSTEM_PROMPT_NATURAL
        user_prompt = get_user_prompt(post.subreddit, post.title, post.selftext)

        logger.info(f"Sending request to Groq model: {config.LLM_MODEL}")
        try:
            completion = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=600,
                timeout=30,
            )
            response = completion.choices[0].message.content
            if not response:
                raise ValueError("Received empty response from Groq")
                
            parsed = parse_structured_response(response, default_title=post.title)
            return parsed["narration"], parsed["title"], parsed["emphasis"]

        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise e
