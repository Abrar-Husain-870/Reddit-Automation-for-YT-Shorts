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
    ) -> dict:
        if not self.api_key:
            raise ValueError("Gemini client not initialized (missing API key)")

        system_prompt = SYSTEM_PROMPT_COMMENTARY if mode == "commentary" else SYSTEM_PROMPT_NATURAL
        user_prompt = get_user_prompt(post.subreddit, post.title, post.selftext)

        candidates = [
            config.LLM_MODEL if config.LLM_MODEL and "gemini" in config.LLM_MODEL.lower() else "gemini-3.6-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-flash-latest"
        ]
        models_to_try = list(dict.fromkeys(candidates))

        logger.info(f"Sending request to Gemini models: {models_to_try}")

        # 1. Try modern google.genai SDK
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            last_err = None
            for model_name in models_to_try:
                try:
                    cfg = types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.8,
                        max_output_tokens=600
                    )
                    res = client.models.generate_content(
                        model=model_name,
                        contents=user_prompt,
                        config=cfg
                    )
                    if res.text:
                        return parse_structured_response(res.text, default_title=post.title)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Gemini narration model '{model_name}' failed: {e}. Retrying...")
            if last_err:
                raise last_err
        except ImportError:
            pass

        # 2. Fallback to legacy google.generativeai if google.genai package is absent
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            last_err = None
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_prompt
                    )
                    response = model.generate_content(
                        user_prompt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.8,
                            max_output_tokens=600,
                        )
                    )
                    if response.text:
                        return parse_structured_response(response.text, default_title=post.title)
                except Exception as e:
                    last_err = e
                    logger.warning(f"Legacy Gemini narration model '{model_name}' failed: {e}. Retrying...")
            if last_err:
                raise last_err
        except ImportError:
            raise ImportError("Neither 'google-genai' nor 'google-generativeai' package is installed.")

        raise ValueError("Received empty response from Gemini API")
