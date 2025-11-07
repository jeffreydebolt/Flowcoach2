"""Tests for environment variable bootstrap functionality."""

import pytest
import os
from unittest.mock import patch, MagicMock
from apps.server.core.env_bootstrap import bootstrap_env


class TestEnvBootstrap:
    """Test environment bootstrap functionality."""

    def test_skips_when_fc_env_production(self):
        """Test that .env loading is skipped when FC_ENV=production."""
        with patch.dict(os.environ, {'FC_ENV': 'production'}, clear=False), \
             patch('dotenv.load_dotenv') as mock_load_dotenv:

            bootstrap_env()

            # Should not call load_dotenv
            mock_load_dotenv.assert_not_called()

    def test_loads_when_fc_auto_load_env_set(self):
        """Test that .env is loaded when FC_AUTO_LOAD_ENV=1."""
        with patch.dict(os.environ, {'FC_ENV': 'production', 'FC_AUTO_LOAD_ENV': '1'}, clear=False), \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('pathlib.Path.exists', return_value=True):

            bootstrap_env()

            # Should call load_dotenv even in production mode
            mock_load_dotenv.assert_called_once()

    def test_skips_when_dotenv_not_available(self):
        """Test that bootstrap is skipped when python-dotenv is not available."""
        with patch.dict(os.environ, {'FC_ENV': 'local'}, clear=False), \
             patch('builtins.__import__', side_effect=ImportError("No module named 'dotenv'")):

            # Should not raise an exception and should complete silently
            bootstrap_env()  # Should complete without error

    def test_skips_when_no_env_file_found(self):
        """Test that bootstrap is skipped when no .env file is found."""
        with patch.dict(os.environ, {'FC_ENV': 'local'}, clear=False), \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('pathlib.Path.exists', return_value=False):

            bootstrap_env()

            # Should not call load_dotenv
            mock_load_dotenv.assert_not_called()

    def test_handles_load_dotenv_exception(self):
        """Test that exceptions during load_dotenv are handled gracefully."""
        with patch.dict(os.environ, {'FC_ENV': 'local'}, clear=False), \
             patch('dotenv.load_dotenv', side_effect=Exception("Load error")), \
             patch('pathlib.Path.exists', return_value=True):

            # Should not raise an exception
            bootstrap_env()

    def test_default_fc_env_is_local(self):
        """Test that default FC_ENV is treated as 'local'."""
        # Remove FC_ENV from environment
        env_copy = os.environ.copy()
        env_copy.pop('FC_ENV', None)

        with patch.dict(os.environ, env_copy, clear=True), \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('pathlib.Path.exists', return_value=True):

            bootstrap_env()

            # Should call load_dotenv since default is 'local'
            mock_load_dotenv.assert_called_once()

    def test_override_false_preserves_existing_env_vars(self):
        """Test that load_dotenv is called with override=False."""
        with patch.dict(os.environ, {'FC_ENV': 'local'}, clear=False), \
             patch('dotenv.load_dotenv') as mock_load_dotenv, \
             patch('pathlib.Path.exists', return_value=True):

            bootstrap_env()

            # Should call load_dotenv with override=False
            mock_load_dotenv.assert_called_once()
            call_kwargs = mock_load_dotenv.call_args[1]
            assert call_kwargs['override'] == False
