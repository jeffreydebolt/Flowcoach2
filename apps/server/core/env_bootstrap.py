"""Environment variable bootstrap for FlowCoach development."""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def bootstrap_env():
    """
    Auto-load .env file when in local development mode.

    Conditions for auto-loading:
    - python-dotenv is available
    - FC_ENV=local (default) or FC_AUTO_LOAD_ENV=1
    - .env file exists in repository root
    """
    # Check if auto-loading is enabled
    fc_env = os.getenv('FC_ENV', 'local').lower()
    auto_load = os.getenv('FC_AUTO_LOAD_ENV', '0') == '1'

    if fc_env != 'local' and not auto_load:
        logger.debug("EnvBootstrap: skipped (not local mode)")
        return

    # Try to import python-dotenv
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.debug("EnvBootstrap: skipped (python-dotenv not available)")
        return

    # Find repository root and .env file
    current_dir = Path(__file__).resolve()
    repo_root = None

    # Walk up directories to find the repository root (where .env should be)
    for parent in [current_dir] + list(current_dir.parents):
        if (parent / '.env').exists():
            repo_root = parent
            break
        # Also check for git root as fallback
        if (parent / '.git').exists() and not repo_root:
            repo_root = parent

    if not repo_root:
        logger.debug("EnvBootstrap: skipped (no .env found)")
        return

    env_path = repo_root / '.env'

    if not env_path.exists():
        logger.debug("EnvBootstrap: skipped (no .env found)")
        return

    # Load the .env file
    try:
        load_dotenv(env_path, override=False)  # Don't override existing env vars
        logger.info("EnvBootstrap: loaded .env via python-dotenv")
    except Exception as e:
        logger.warning(f"EnvBootstrap: failed to load .env: {e}")


# Auto-bootstrap on import in development
if __name__ != '__main__':
    bootstrap_env()
