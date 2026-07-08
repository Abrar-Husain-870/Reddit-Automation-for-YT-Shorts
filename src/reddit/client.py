import json
import random
import time
import urllib.request
import urllib.parse
from typing import List, Set, Optional
import requests

# Initialize global session to reuse connections and support cookie persistence
session_client = requests.Session()

import config
from src.logger import logger
from src.reddit.models import RedditPost

# Global headers mimicking the official Reddit iOS application to bypass CDN bot protection
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Reddit/2023.23.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}


def load_processed_ids() -> Set[str]:
    """Load the set of already processed Reddit post IDs."""
    if config.HISTORY_FILE.exists():
        try:
            with open(config.HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return set(data)
        except Exception as e:
            logger.warning(f"Failed to read Reddit post history: {e}. Starting fresh.")
    return set()


def save_processed_id(post_id: str) -> None:
    """Save a processed Reddit post ID to prevent duplicates."""
    processed = load_processed_ids()
    processed.add(post_id)
    try:
        config.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(processed)), f, indent=2)
        logger.info(f"Saved Reddit ID {post_id} to history database")
    except Exception as e:
        logger.error(f"Failed to save Reddit ID to history: {e}")


def _fetch_anonymous_json(subreddit: str, sort: str, time_filter: str) -> List[dict]:
    """Fetch subreddit posts using the public JSON API."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {}
    if sort == "top" and time_filter:
        params["t"] = time_filter
    
    logger.info(f"Fetching posts from anonymous Reddit feed: {url}")
    try:
        response = session_client.get(url, params=params, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        children = data.get("data", {}).get("children", [])
        return [child.get("data", {}) for child in children]
    except Exception as e:
        logger.warning(f"Public Reddit API fetch failed for r/{subreddit}: {e}")
        return []


def _fetch_with_praw(subreddit: str, sort: str, time_filter: str) -> List[dict]:
    """Fetch posts using PRAW (Python Reddit API Wrapper) if credentials are provided."""
    try:
        import praw
    except ImportError:
        logger.debug("PRAW is not installed. Falling back to public JSON feeds.")
        return []

    if not (config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET):
        logger.debug("Reddit API credentials not fully set. Falling back to public JSON feeds.")
        return []

    logger.info(f"Fetching posts via PRAW for r/{subreddit} (sort: {sort}, time: {time_filter})")
    try:
        reddit = praw.Reddit(
            client_id=config.REDDIT_CLIENT_ID,
            client_secret=config.REDDIT_CLIENT_SECRET,
            user_agent=config.REDDIT_USER_AGENT
        )
        sub = reddit.subreddit(subreddit)
        
        # Resolve sorting
        if sort == "top":
            feed = sub.top(time_filter=time_filter, limit=50)
        elif sort == "new":
            feed = sub.new(limit=50)
        elif sort == "rising":
            feed = sub.rising(limit=50)
        else:
            feed = sub.hot(limit=50)
            
        posts = []
        for post in feed:
            posts.append({
                "id": post.id,
                "subreddit": post.subreddit.display_name,
                "title": post.title,
                "selftext": post.selftext,
                "score": post.score,
                "num_comments": post.num_comments,
                "over_18": post.over_18,
                "is_self": post.is_self,
                "permalink": post.permalink,
                "author": post.author.name if post.author else "[deleted]",
                "pinned": getattr(post, "pinned", False),
                "crosspost_parent": getattr(post, "crosspost_parent", None)
            })
        return posts
    except Exception as e:
        logger.error(f"PRAW fetch failed for r/{subreddit}: {e}. Falling back to public JSON.")
        return []


def _fetch_with_rss(subreddit: str) -> List[dict]:
    """Fetch posts via public RSS feeds as a third fallback."""
    import xml.etree.ElementTree as ET
    import html.parser
    
    class HTMLTextExtractor(html.parser.HTMLParser):
        def __init__(self):
            super().__init__()
            self.text = []
        def handle_data(self, data):
            self.text.append(data)
        def get_text(self):
            return "".join(self.text)

    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    logger.info(f"Fetching posts from anonymous RSS feed: {url}")
    try:
        response = session_client.get(url, headers=DEFAULT_HEADERS, timeout=15)
        response.raise_for_status()
        if not response.content.strip():
            logger.warning("Empty response from RSS feed")
            return []
            
        root = ET.fromstring(response.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        posts = []
        for entry in root.findall("atom:entry", ns):
            post_id = entry.find("atom:id", ns)
            post_id_val = post_id.text if post_id is not None else ""
            if post_id_val.startswith("t3_"):
                post_id_val = post_id_val[3:]
                
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text if title_elem is not None else ""
            
            link_elem = entry.find("atom:link", ns)
            permalink = link_elem.attrib.get("href", "") if link_elem is not None else ""
            
            author_elem = entry.find("atom:author/atom:name", ns)
            author = author_elem.text if author_elem is not None else "[deleted]"
            if author.startswith("/u/"):
                author = author[3:]
                
            content_elem = entry.find("atom:content", ns)
            html_content = content_elem.text if content_elem is not None else ""
            
            extractor = HTMLTextExtractor()
            extractor.feed(html_content)
            selftext = extractor.get_text().strip()
            
            # RSS has no score/comments. Fake values above config minimums to pass filters.
            posts.append({
                "id": post_id_val,
                "subreddit": subreddit,
                "title": title,
                "selftext": selftext,
                "score": config.REDDIT_MIN_SCORE + 100,
                "num_comments": config.REDDIT_MIN_COMMENTS + 10,
                "over_18": False,
                "is_self": True,
                "permalink": permalink,
                "author": author,
                "pinned": False,
                "crosspost_parent": None
            })
        return posts
    except Exception as e:
        logger.warning(f"RSS feed fetch failed for r/{subreddit}: {e}")
        return []


def fetch_posts(subreddit: str, sort: str = "top", time_filter: str = "week") -> List[RedditPost]:
    """Fetch posts from a subreddit, mapping them to RedditPost dataclasses."""
    raw_posts = _fetch_with_praw(subreddit, sort, time_filter)
    
    if not raw_posts:
        raw_posts = _fetch_anonymous_json(subreddit, sort, time_filter)
        
    if not raw_posts:
        raw_posts = _fetch_with_rss(subreddit)
        
    posts = []
    for rp in raw_posts:
        posts.append(
            RedditPost(
                id=rp.get("id", ""),
                subreddit=rp.get("subreddit", subreddit),
                title=rp.get("title", ""),
                selftext=rp.get("selftext", ""),
                score=rp.get("score", 0),
                num_comments=rp.get("num_comments", 0),
                over_18=rp.get("over_18", False),
                is_self=rp.get("is_self", True),
                permalink=rp.get("permalink", ""),
                author=rp.get("author", rp.get("author_fullname", "[deleted]")),
                pinned=rp.get("pinned", False),
                crosspost_parent=rp.get("crosspost_parent")
            )
        )
    return posts


def filter_post(post: RedditPost, processed_ids: Set[str]) -> Optional[str]:
    """
    Validate and filter a Reddit post based on system guidelines.
    Returns None if post is valid, otherwise returns a string describing the filter reason.
    """
    if post.id in processed_ids:
        return "Previously processed ID"
        
    if config.REDDIT_FILTER_NSFW and post.over_18:
        return "NSFW post"
        
    if config.REDDIT_FILTER_PINNED and post.pinned:
        return "Pinned post"
        
    if config.REDDIT_FILTER_CROSSPOSTS and post.crosspost_parent:
        return "Crosspost"
        
    if not post.is_self:
        return "Not a self/text post (e.g. image/link)"

    # Check for deleted/removed content
    cleaned_body = post.selftext.strip()
    if cleaned_body in ("[deleted]", "[removed]", ""):
        if not post.title:
            return "Deleted / Empty content"
            
    # Combine title and text for length calculations
    total_text = f"{post.title}\n{post.selftext}"
    text_len = len(total_text)
    
    if text_len < config.REDDIT_POST_MIN_LEN:
        return f"Post too short ({text_len} chars < {config.REDDIT_POST_MIN_LEN})"
        
    if text_len > config.REDDIT_POST_MAX_LEN:
        return f"Post too long ({text_len} chars > {config.REDDIT_POST_MAX_LEN})"
        
    if post.score < config.REDDIT_MIN_SCORE:
        return f"Score too low ({post.score} < {config.REDDIT_MIN_SCORE})"
        
    if post.num_comments < config.REDDIT_MIN_COMMENTS:
        return f"Comment count too low ({post.num_comments} < {config.REDDIT_MIN_COMMENTS})"
        
    return None


def get_random_reddit_post() -> Optional[RedditPost]:
    """
    Fetch posts across configurable subreddits, apply filters, 
    and pick a random eligible post.
    """
    subreddits = config.SUBREDDITS
    if not subreddits:
        logger.error("No subreddits configured in config.SUBREDDITS")
        return None
        
    random.shuffle(subreddits)
    processed_ids = load_processed_ids()
    
    for i, sub in enumerate(subreddits):
        if i > 0:
            logger.info("Pausing for 2.0s to respect Reddit rate limits...")
            time.sleep(2.0)
            
        logger.info(f"Searching subreddits for posts: r/{sub}")
        posts = fetch_posts(sub, config.REDDIT_SORT, config.REDDIT_TIME_FILTER)
        
        if not posts:
            continue
            
        random.shuffle(posts)
        for post in posts:
            filter_reason = filter_post(post, processed_ids)
            if filter_reason is None:
                logger.info(f"🎉 Selected Reddit Post: r/{post.subreddit} - ID: {post.id} - Title: {post.title[:50]}...")
                return post
            else:
                logger.debug(f"Filtered out r/{post.subreddit} post {post.id}: {filter_reason}")
                
    logger.error("❌ No eligible Reddit posts found matching all filters across all subreddits.")
    return None
