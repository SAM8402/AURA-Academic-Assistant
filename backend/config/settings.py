"""
Application configuration settings.

This module manages all configuration settings using environment variables
with sensible defaults for development. For production, set proper environment
variables in your deployment environment.
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings with environment variable support.

    All settings can be overridden using environment variables.
    Create a .env file in the backend directory for local development.

    Example .env file:
        # Application
        APP_NAME=AURA
        DEBUG=True

        # Security
        SECRET_KEY=your-super-secret-key-change-in-production
        ACCESS_TOKEN_EXPIRE_MINUTES=60
        REFRESH_TOKEN_EXPIRE_DAYS=7

        # Database
        DATABASE_URL=sqlite:///./app.db
    """

    # Application Settings
    APP_NAME: str = Field(
        default="AURA",
        description="Application name"
    )
    APP_VERSION: str = Field(
        default="1.0.0",
        description="API version"
    )
    DEBUG: bool = Field(
        default=True,
        description="Debug mode"
    )
    API_PREFIX: str = Field(
        default="/api",
        description="API route prefix"
    )

    # Security Settings
    SECRET_KEY: str = Field(
        default="change_me_generate_with_secrets_token_hex_32",
        description="Secret key for JWT encoding (REQUIRED - set in .env)"
    )
    ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )

    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(
        default=True,
        description="Allow credentials in CORS"
    )
    CORS_ALLOW_METHODS: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        description="Allowed HTTP methods"
    )
    CORS_ALLOW_HEADERS: List[str] = Field(
        default=["Content-Type", "Authorization", "Accept", "X-Requested-With"],
        description="Allowed HTTP headers"
    )

    # Database Settings
    DATABASE_URL: str = Field(
        default="sqlite:///./app.db",
        description="Database connection URL"
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries (for debugging)"
    )

    # Pagination Settings
    DEFAULT_PAGE_SIZE: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Default pagination page size"
    )
    MAX_PAGE_SIZE: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum pagination page size"
    )

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="Maximum file upload size in bytes"
    )
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".doc", ".docx", ".txt", ".jpg", ".jpeg", ".png", ".mp4", ".zip"],
        description="Allowed file extensions for upload"
    )
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Directory for uploaded files"
    )

    # Rate Limiting (for future implementation)
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        description="API rate limit per minute per user"
    )

    # Email Settings (for future implementation)
    SMTP_HOST: str = Field(
        default="smtp.gmail.com",
        description="SMTP server host"
    )
    SMTP_PORT: int = Field(
        default=587,
        description="SMTP server port"
    )
    SMTP_USER: str = Field(
        default="",
        description="SMTP username"
    )
    SMTP_PASSWORD: str = Field(
        default="",
        description="SMTP password"
    )
    EMAILS_FROM_EMAIL: str = Field(
        default="noreply@aura.edu",
        description="From email address"
    )
    EMAILS_FROM_NAME: str = Field(
        default="AURA - Academic Assistant",
        description="From email name"
    )
    SMTP_TLS: bool = Field(
        default=True,
        description="Use TLS for SMTP connection"
    )
    SMTP_SSL: bool = Field(
        default=False,
        description="Use SSL for SMTP connection"
    )

    # AI/LLM Settings (Gemini)
    GOOGLE_API_KEY: str = Field(
        default="your-google-api-key",
        description="Google Gemini API Key (REQUIRED - get from https://makersuite.google.com/app/apikey)"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use (gemini-2.5-flash, gemini-2.5-pro, gemini-flash-latest, gemini-pro-latest)"
    )
    GEMINI_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Temperature for response randomness (0.0-1.0)"
    )
    GEMINI_MAX_TOKENS: int = Field(
        default=1024,
        description="Maximum tokens in response"
    )
    CHATBOT_SYSTEM_PROMPT: str = Field(
        default="""You are AURA (Academic Unified Response Assistant), an AI teaching assistant for students.
        You help with academic questions, provide explanations, and assist with learning.
        Be helpful, educational, and encouraging. Keep responses clear and concise.""",
        description="System prompt for chatbot"
    )

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance
settings = Settings()


# Validate required settings on import
if not settings.SECRET_KEY or settings.SECRET_KEY == "change_me_generate_with_secrets_token_hex_32":
    import warnings
    warnings.warn(
        "SECRET_KEY is not set! Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'",
        stacklevel=2
    )

if not settings.GOOGLE_API_KEY:
    import warnings
    warnings.warn(
        "GOOGLE_API_KEY is not set! AI features will not work. "
        "Get a key from: https://makersuite.google.com/app/apikey",
        stacklevel=2
    )


# Helper function to get settings
def get_settings() -> Settings:
    """
    Get application settings.

    Returns:
        Settings: Application settings instance

    Usage:
        from config.settings import get_settings
        settings = get_settings()
        print(settings.APP_NAME)
    """
    return settings
