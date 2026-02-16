"""
Configuration settings for the transaction analytics service.
"""

import os
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Database settings
    database_url: str = Field(
        default="postgresql://user:password@localhost/transaction_analytics",
        description="PostgreSQL database URL"
    )
    
    # Application settings
    app_name: str = Field(default="Transaction Analytics API", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    
    # API settings
    api_prefix: str = Field(default="/api/v1", description="API prefix")
    
    # Test database settings
    test_database_url: str = Field(
        default="postgresql://user:password@localhost/test_transaction_analytics",
        description="Test database URL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
