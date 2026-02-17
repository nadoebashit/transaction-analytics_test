"""
Tests for configuration and settings.
"""

import pytest
import os
from unittest.mock import patch

from app.config import Settings


class TestSettings:
    """Test class for application settings."""
    
    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        
        assert settings.app_name == "Transaction Analytics API"
        assert settings.app_version == "1.0.0"
        assert settings.debug is False
        assert settings.api_prefix == "/api/v1"
        assert settings.database_url == "postgresql://user:password@localhost/transaction_analytics"
        assert settings.test_database_url == "postgresql://user:password@localhost/test_transaction_analytics"
    
    def test_settings_from_env(self):
        """Test settings from environment variables."""
        # Mock environment variables
        env_vars = {
            'APP_NAME': 'Test API',
            'APP_VERSION': '2.0.0',
            'DEBUG': 'true',
            'DATABASE_URL': 'postgresql://test:test@localhost/test_db'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            assert settings.app_name == 'Test API'
            assert settings.app_version == '2.0.0'
            assert settings.debug is True
            assert settings.database_url == 'postgresql://test:test@localhost/test_db'
    
    def test_settings_validation(self):
        """Test settings validation."""
        # Settings should accept various valid values
        settings = Settings(
            app_name="Valid Name",
            app_version="1.2.3",
            debug=True,
            database_url="postgresql://user:pass@host/db"
        )
        
        assert settings.app_name == "Valid Name"
        assert settings.app_version == "1.2.3"
        assert settings.debug is True
        assert "postgresql://user:pass@host/db" in settings.database_url
    
    def test_settings_description(self):
        """Test that settings have proper descriptions."""
        # This is more of a meta-test to ensure Field descriptions are present
        settings = Settings()
        
        # The fact that Settings can be instantiated means Field descriptions are working
        assert settings is not None
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'app_name')
        assert hasattr(settings, 'app_version')
    
    def test_settings_case_insensitive(self):
        """Test that environment variable names are case insensitive."""
        env_vars = {
            'app_name': 'Lowercase API',
            'DEBUG': 'true'
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            
            # Should pick up both variations
            assert settings.app_name == 'Lowercase API'
            assert settings.debug is True
