"""
WSGI entry point for production deployment.

Usage with Gunicorn:
    gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 wsgi:app

Usage with Waitress (Windows):
    waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from api import app

if __name__ == "__main__":
    app.run()
