"""
Application Configuration
Central place for all configuration values
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env variables are available before reading any settings so that
# deploying without exporting env vars still works.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Admin Authentication
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Timeout Settings (in seconds)
# Default timeout for all external service requests
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))

# IMAP connection timeout
IMAP_TIMEOUT = int(os.getenv("IMAP_TIMEOUT", str(DEFAULT_TIMEOUT)))

# HTTP request timeout
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT", str(DEFAULT_TIMEOUT)))

# Logging Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
