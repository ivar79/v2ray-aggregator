"""
Configuration management for V2Ray Aggregator.

Loads configuration from environment variables and provides type-safe access.
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Telegram API Credentials
    telegram_api_id: int = Field(..., description="Telegram API ID")
    telegram_api_hash: str = Field(..., description="Telegram API Hash")
    telegram_bot_token: str = Field(..., description="Telegram Bot Token")
    
    # GitHub Configuration
    github_token: str = Field(..., description="GitHub Personal Access Token")
    github_owner: str = Field(..., description="GitHub repository owner")
    github_repo: str = Field(..., description="GitHub repository name")
    github_branch: str = Field(default="main", description="GitHub branch name")
    
    # Channel Branding
    channel_name: str = Field(..., description="Operator's channel name")
    channel_username: str = Field(..., description="Operator's channel username (e.g., @mychannel)")
    channel_id: str = Field(..., description="Operator's channel ID")
    
    # Admin Authorization
    admin_user_ids: str = Field(
        default="",
        description="Comma-separated list of authorized Telegram user IDs"
    )
    
    @property
    def admin_user_ids_list(self) -> List[int]:
        """Parse admin_user_ids string into list of integers."""
        if not self.admin_user_ids:
            return []
        return [int(uid.strip()) for uid in self.admin_user_ids.split(',') if uid.strip()]
    
    # Collection Settings
    collection_interval_minutes: int = Field(
        default=30,
        description="Interval between scheduled collections in minutes"
    )
    first_run_message_limit: int = Field(
        default=5000,
        description="Maximum messages to fetch on first run"
    )
    
    # Document Processing
    max_document_size_mb: float = Field(
        default=10.0,
        description="Maximum document size in MB to process"
    )
    
    # Operational Settings
    dry_run: bool = Field(
        default=True,
        description="If true, skip GitHub publishing and destructive operations"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Database
    database_path: str = Field(
        default="v2ray_aggregator.db",
        description="Path to SQLite database file"
    )
    
    # Session
    telegram_session_name: str = Field(
        default="v2ray_aggregator_session",
        description="Telethon session file name"
    )
    
    @field_validator('log_level')
    @classmethod
    def uppercase_log_level(cls, v):
        """Ensure log level is uppercase."""
        return v.upper() if isinstance(v, str) else v
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        case_sensitive = False


def load_settings() -> Settings:
    """
    Load settings from environment variables.
    
    Returns:
        Settings: Validated settings object
        
    Raises:
        ValidationError: If required environment variables are missing or invalid
    """
    # Load .env file if it exists
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    
    return Settings()


# Global settings instance
settings: Settings | None = None


def get_settings() -> Settings:
    """
    Get global settings instance, loading if necessary.
    
    Returns:
        Settings: Application settings
    """
    global settings
    if settings is None:
        settings = load_settings()
    return settings
