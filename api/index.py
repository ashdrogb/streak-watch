"""
Vercel serverless function entry point.

Vercel's Python runtime auto-detects files in the api/ directory and serves
them as serverless functions. This file just adds the backend/ directory to
sys.path so all the existing imports (config, models, providers/, etc.) keep
working exactly as they did locally, then re-exports the Flask `app` object
that Vercel needs to receive requests.

All the actual logic stays in backend/ -- nothing there needs to change.
"""
import sys
import os

# Make backend/ importable so `from config import ...`, `from models import ...`
# etc. all resolve the same way they do when running `python server.py` locally.
_backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
sys.path.insert(0, os.path.abspath(_backend_dir))

from server import app  # noqa: F401 -- Vercel needs the name `app` in this module
