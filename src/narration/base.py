from abc import ABC, abstractmethod
from typing import Tuple, List

from src.reddit.models import RedditPost

class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM Narration Providers."""
    
    @abstractmethod
    def generate_narration(
        self, 
        post: RedditPost, 
        mode: str = "commentary", 
        style: str = "chaotic"
    ) -> Tuple[str, str, List[str]]:
        """
        Generate narration script from a Reddit post.
        
        Args:
            post: The RedditPost dataclass instance.
            mode: Narration mode ('natural' or 'commentary').
            style: Presentation style ('chaotic', 'meme', 'story', 'npc').
            
        Returns:
            Tuple of (full_narration_text, clickbait_title, emphasis_words_list)
        """
        pass
