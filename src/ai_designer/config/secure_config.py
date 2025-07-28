"""
Secure Configuration Management
Handles environment variables and API keys securely
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing"""
    pass

class SecureConfig:
    """
    Secure configuration management for the AI Designer system.
    
    This class handles:
    - Loading environment variables from .env files
    - Validating required configuration
    - Providing secure access to sensitive values
    - Never logging or exposing sensitive information
    """
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize secure configuration.
        
        Args:
            env_file: Path to .env file (optional, defaults to .env in project root)
        """
        self._config: Dict[str, Any] = {}
        self._sensitive_keys = {
            'GOOGLE_API_KEY',
            'REDIS_PASSWORD', 
            'DATABASE_PASSWORD',
            'SECRET_KEY',
            'JWT_SECRET'
        }
        
        # Load environment variables
        self._load_env_file(env_file)
        self._load_from_environment()
        self._validate_configuration()
    
    def _load_env_file(self, env_file: Optional[str] = None) -> None:
        """Load environment variables from .env file"""
        if env_file is None:
            # Look for .env file in project root
            project_root = Path(__file__).parent.parent.parent
            env_file = project_root / '.env'
        
        env_path = Path(env_file)
        
        if not env_path.exists():
            logger.warning(f"Environment file not found: {env_path}")
            logger.info("Using system environment variables only")
            return
        
        try:
            with open(env_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE format
                    if '=' not in line:
                        logger.warning(f"Invalid line {line_num} in {env_path}: {line}")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Don't override existing environment variables
                    if key not in os.environ:
                        os.environ[key] = value
                        
        except Exception as e:
            logger.error(f"Error loading environment file {env_path}: {e}")
            raise ConfigurationError(f"Failed to load environment file: {e}")
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables"""
        # Required configuration
        required_keys = [
            'GOOGLE_API_KEY'
        ]
        
        # Optional configuration with defaults
        optional_config = {
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'REDIS_DB': '0',
            'DEBUG': 'false',
            'LOG_LEVEL': 'INFO',
            'SESSION_TIMEOUT': '3600',
            'MAX_CONCURRENT_SESSIONS': '10',
            'FREECAD_PATH': '',
            'FREECAD_PYTHON_PATH': ''
        }
        
        # Load required configuration
        for key in required_keys:
            value = os.environ.get(key)
            if not value:
                raise ConfigurationError(
                    f"Required environment variable '{key}' is not set. "
                    f"Please check your .env file or set it in your environment."
                )
            self._config[key] = value
        
        # Load optional configuration
        for key, default_value in optional_config.items():
            self._config[key] = os.environ.get(key, default_value)
    
    def _validate_configuration(self) -> None:
        """Validate configuration values"""
        # Validate Google API key format
        api_key = self._config.get('GOOGLE_API_KEY', '')
        if not api_key.startswith('AIza'):
            logger.warning("Google API key format may be invalid (should start with 'AIza')")
        
        if len(api_key) < 30:
            logger.warning("Google API key appears to be too short")
        
        # Convert string values to appropriate types
        try:
            self._config['REDIS_PORT'] = int(self._config['REDIS_PORT'])
            self._config['REDIS_DB'] = int(self._config['REDIS_DB'])
            self._config['SESSION_TIMEOUT'] = int(self._config['SESSION_TIMEOUT'])
            self._config['MAX_CONCURRENT_SESSIONS'] = int(self._config['MAX_CONCURRENT_SESSIONS'])
            self._config['DEBUG'] = self._config['DEBUG'].lower() == 'true'
        except ValueError as e:
            raise ConfigurationError(f"Invalid configuration value: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def get_api_key(self) -> str:
        """
        Get Google API key securely.
        
        Returns:
            Google API key
            
        Raises:
            ConfigurationError: If API key is not configured
        """
        api_key = self._config.get('GOOGLE_API_KEY')
        if not api_key:
            raise ConfigurationError(
                "Google API key is not configured. "
                "Please set GOOGLE_API_KEY in your .env file."
            )
        return api_key
    
    def get_redis_config(self) -> Dict[str, Any]:
        """
        Get Redis configuration.
        
        Returns:
            Dictionary with Redis connection parameters
        """
        return {
            'host': self._config.get('REDIS_HOST', 'localhost'),
            'port': self._config.get('REDIS_PORT', 6379),
            'db': self._config.get('REDIS_DB', 0),
            'password': self._config.get('REDIS_PASSWORD')  # May be None
        }
    
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return self._config.get('DEBUG', False)
    
    def get_log_level(self) -> str:
        """Get logging level"""
        return self._config.get('LOG_LEVEL', 'INFO')
    
    def __str__(self) -> str:
        """String representation (safe - doesn't expose sensitive values)"""
        safe_config = {}
        for key, value in self._config.items():
            if key in self._sensitive_keys:
                # Mask sensitive values
                if isinstance(value, str) and len(value) > 8:
                    safe_config[key] = f"{value[:4]}...{value[-4:]}"
                else:
                    safe_config[key] = "***"
            else:
                safe_config[key] = value
        
        return f"SecureConfig({safe_config})"
    
    def __repr__(self) -> str:
        """Representation (safe)"""
        return self.__str__()

# Global configuration instance
_config: Optional[SecureConfig] = None

def get_config() -> SecureConfig:
    """
    Get global configuration instance.
    
    Returns:
        SecureConfig instance
    """
    global _config
    if _config is None:
        _config = SecureConfig()
    return _config

def get_api_key() -> str:
    """
    Convenience function to get API key.
    
    Returns:
        Google API key
    """
    return get_config().get_api_key()

def reload_config(env_file: Optional[str] = None) -> SecureConfig:
    """
    Reload configuration from environment.
    
    Args:
        env_file: Path to .env file (optional)
        
    Returns:
        New SecureConfig instance
    """
    global _config
    _config = SecureConfig(env_file)
    return _config
