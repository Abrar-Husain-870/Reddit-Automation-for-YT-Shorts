from typing import Tuple, List

import config
from src.logger import logger
from src.narration.base import BaseLLMProvider
from src.narration.helpers import parse_structured_response
from src.narration.prompts import SYSTEM_PROMPT_COMMENTARY, SYSTEM_PROMPT_NATURAL, get_user_prompt
from src.reddit.models import RedditPost


class OpenAILikeProvider(BaseLLMProvider):
    """OpenAI-compatible provider supporting OpenAI, DeepSeek, OpenRouter, and local Ollama."""

    def __init__(self) -> None:
        self.provider = config.LLM_PROVIDER.lower()
        self.api_key = ""
        self.base_url = None

        if self.provider == "openai":
            self.api_key = config.OPENAI_API_KEY
            self.base_url = None
        elif self.provider == "deepseek":
            self.api_key = config.DEEPSEEK_API_KEY
            self.base_url = "https://api.deepseek.com"
        elif self.provider == "openrouter":
            self.api_key = config.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1"
        elif self.provider == "ollama":
            self.api_key = "ollama"  # dummy key
            self.base_url = config.OLLAMA_API_URL

        if not self.api_key and self.provider != "ollama":
            logger.warning(f"{self.provider.upper()} API key is not configured.")

    def generate_narration(
        self, 
        post: RedditPost, 
        mode: str = "commentary", 
        style: str = "chaotic"
    ) -> Tuple[str, str, List[str]]:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for this LLM provider. "
                "Please run: pip install openai"
            )

        client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)
        system_prompt = SYSTEM_PROMPT_COMMENTARY if mode == "commentary" else SYSTEM_PROMPT_NATURAL
        user_prompt = get_user_prompt(post.subreddit, post.title, post.selftext)

        logger.info(f"Sending request to OpenAI-compatible provider ({self.provider}) model: {config.LLM_MODEL}")
        try:
            completion = client.chat.completions.create(
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
                raise ValueError("Received empty response from LLM")

            parsed = parse_structured_response(response, default_title=post.title)
            return parsed["narration"], parsed["title"], parsed["emphasis"]

        except Exception as e:
            logger.error(f"{self.provider.upper()} API error: {e}")
            raise e
