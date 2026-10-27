"""Application settings, read from environment variables.

Secrets (such as an AI API key) are never written in the code. They are
loaded from a local .env file that is excluded from Git.
"""

import os

from dotenv import load_dotenv

load_dotenv()

APP_VERSION = "0.1.0"
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
