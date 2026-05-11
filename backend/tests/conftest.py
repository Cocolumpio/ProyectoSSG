"""Shared fixtures and env loading for backend tests."""
import os
from pathlib import Path


def _load_frontend_env():
    """Load REACT_APP_BACKEND_URL from /app/frontend/.env if not set."""
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return
    env_file = Path("/app/frontend/.env")
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_frontend_env()
