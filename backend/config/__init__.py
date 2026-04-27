"""
Centralized Configuration Package for AURA Backend.

All application configuration & infrastructure lives here:
- settings.py            : App settings (env vars, DB, CORS, Gemini, SMTP)
- db.py                  : Database engine, sessions, Base class, get_db()
- security.py            : JWT, password hashing, auth helpers
- sample_chart_data.json : Sample data for chart generation

Usage:
    from config.settings import settings
    from config.db import get_db, Base, SessionLocal
    from config.security import hash_password, create_tokens
"""

from .settings import settings, get_settings

__all__ = ["settings", "get_settings"]
