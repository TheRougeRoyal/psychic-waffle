import sys
import os

# Ensure the project root is on the path so all modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: F401 — Vercel needs the `app` symbol in this file

# Re-export for Vercel's Python runtime
__all__ = ["app"]
