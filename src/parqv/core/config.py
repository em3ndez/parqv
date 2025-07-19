"""
Configuration constants and settings for parqv application.
"""

from typing import Dict, Type, List
from pathlib import Path

# File extensions and their corresponding handler types
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".parquet": "parquet",
    ".json": "json", 
    ".ndjson": "json",
    ".csv": "csv"
}

# Application constants
LOG_FILENAME = "parqv.log"
LOG_MAX_BYTES = 1024 * 1024 * 5  # 5MB
LOG_BACKUP_COUNT = 3
LOG_ENCODING = "utf-8"

# UI Constants
DEFAULT_PREVIEW_ROWS = 50

# CSS Path (relative to the app module)
CSS_PATH = "parqv.css" 