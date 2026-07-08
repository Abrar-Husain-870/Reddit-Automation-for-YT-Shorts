from dataclasses import dataclass
from typing import Optional

@dataclass
class RedditPost:
    """Represents a Reddit post with all metadata required for filtering and narration."""
    id: str
    subreddit: str
    title: str
    selftext: str
    score: int
    num_comments: int
    over_18: bool
    is_self: bool
    permalink: str
    author: str
    pinned: bool = False
    crosspost_parent: Optional[str] = None

    @property
    def url(self) -> str:
        """Returns the full URL of the Reddit post."""
        return f"https://www.reddit.com{self.permalink}"
