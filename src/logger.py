import logging
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Any

from config import ROOT

# Ensure logs directory exists
LOG_DIR = ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "pipeline.log"

# Create a rotating file handler (5MB per file, max 5 backup files)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
console_handler = logging.StreamHandler()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger("RedditShortsPipeline")

# Track active stage timings
_stage_start_times: Dict[str, float] = {}


def log_stage_start(stage_name: str) -> None:
    """Log the beginning of a pipeline stage."""
    _stage_start_times[stage_name] = time.time()
    logger.info(f"▶ STARTING STAGE: {stage_name}")


def log_stage_finish(stage_name: str, metadata: Dict[str, Any] | None = None) -> None:
    """Log the successful completion of a pipeline stage, including duration."""
    start_time = _stage_start_times.pop(stage_name, None)
    duration_str = ""
    if start_time is not None:
        duration = time.time() - start_time
        duration_str = f" in {duration:.2f}s"
    
    meta_str = f" | Metadata: {metadata}" if metadata else ""
    logger.info(f"✔ FINISHED STAGE: {stage_name}{duration_str}{meta_str}")


def log_stage_error(stage_name: str, error: Exception | str, fatal: bool = False) -> None:
    """Log an error occurring in a pipeline stage."""
    start_time = _stage_start_times.pop(stage_name, None)
    duration_str = ""
    if start_time is not None:
        duration = time.time() - start_time
        duration_str = f" (failed after {duration:.2f}s)"
    
    level = "FATAL" if fatal else "ERROR"
    logger.error(f"❌ {level} IN STAGE: {stage_name}{duration_str} — {error}")
