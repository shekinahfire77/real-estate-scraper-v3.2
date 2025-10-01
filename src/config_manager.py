"""Configuration management using YAML files"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseSettings
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ConfigManager:
    """Manage configuration from YAML files and environment variables"""
    
    def __init__(self, config_file: str = 'config.yaml'):
        """Initialize configuration manager
        
        Args:
            config_file: Path to YAML configuration file
        """
        
        self.config_file = Path(config_file)
        self.config = self.load_config()
        self.apply_env_overrides()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file
        
        Returns:
            Configuration dictionary
        """
        
        if not self.config_file.exists():
            logger.warning(f"Config file {self.config_file} not found, using defaults")
            return self.get_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {self.config_file}")
                return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.get_default_config()
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration
        
        Returns:
            Default configuration dictionary
        """
        
        return {
            'scraping': {
                'concurrent_limit': 5,
                'quality_threshold': 50,
                'timeout': 30,
                'use_async': True,
                'retry': {
                    'max_attempts': 3,
                    'base_delay': 1.0,
                    'max_delay': 60.0
                },
                'circuit_breaker': {
                    'failure_threshold': 5,
                    'recovery_timeout': 60,
                    'block_duration_days': 7
                }
            },
            'database': {
                'type': 'sqlite',
                'sqlite': {
                    'path': 'data/real_estate.db'
                },
                'postgresql': {
                    'host': 'localhost',
                    'port': 5432,
                    'user': 'postgres',
                    'password': 'postgres',
                    'database': 'real_estate'
                }
            },
            'export': {
                'default_format': 'csv',
                'output_dir': 'data/exports',
                'include_metadata': True,
                'compress': False
            },
            'monitoring': {
                'dashboard': {
                    'enabled': False,
                    'port': 8050,
                    'host': 'localhost'
                }
            },
            'logging': {
                'level': 'INFO',
                'file': {
                    'enabled': True,
                    'path': 'logs/scraper.log'
                }
            }
        }
    
    def apply_env_overrides(self):
        """Apply environment variable overrides to configuration"""
        
        # Database overrides
        if os.getenv('DB_TYPE'):
            self.config['database']['type'] = os.getenv('DB_TYPE')
        
        if os.getenv('DB_HOST'):
            self.config['database']['postgresql']['host'] = os.getenv('DB_HOST')
        
        if os.getenv('DB_PORT'):
            self.config['database']['postgresql']['port'] = int(os.getenv('DB_PORT'))
        
        if os.getenv('DB_USER'):
            self.config['database']['postgresql']['user'] = os.getenv('DB_USER')
        
        if os.getenv('DB_PASSWORD'):
            self.config['database']['postgresql']['password'] = os.getenv('DB_PASSWORD')
        
        if os.getenv('DB_NAME'):
            self.config['database']['postgresql']['database'] = os.getenv('DB_NAME')
        
        # Scraping overrides
        if os.getenv('DEFAULT_CONCURRENT_LIMIT'):
            self.config['scraping']['concurrent_limit'] = int(os.getenv('DEFAULT_CONCURRENT_LIMIT'))
        
        if os.getenv('DEFAULT_QUALITY_THRESHOLD'):
            self.config['scraping']['quality_threshold'] = int(os.getenv('DEFAULT_QUALITY_THRESHOLD'))
        
        # Logging overrides
        if os.getenv('LOG_LEVEL'):
            self.config['logging']['level'] = os.getenv('LOG_LEVEL')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports nested keys with dots)
        
        Args:
            key: Configuration key (e.g., 'database.type')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by key
        
        Args:
            key: Configuration key (e.g., 'database.type')
            value: Value to set
        """
        
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self, filename: Optional[str] = None):
        """Save configuration to file
        
        Args:
            filename: Output filename (uses original if not specified)
        """
        
        output_file = filename or self.config_file
        
        try:
            with open(output_file, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=True)
            logger.info(f"Saved configuration to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def validate(self) -> bool:
        """Validate configuration
        
        Returns:
            True if valid, False otherwise
        """
        
        # Check required fields
        required_fields = [
            'scraping.concurrent_limit',
            'scraping.quality_threshold',
            'database.type',
            'export.default_format'
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                logger.error(f"Required configuration field missing: {field}")
                return False
        
        # Validate values
        if self.get('scraping.concurrent_limit') < 1:
            logger.error("Concurrent limit must be at least 1")
            return False
        
        if self.get('scraping.quality_threshold') < 0 or self.get('scraping.quality_threshold') > 100:
            logger.error("Quality threshold must be between 0 and 100")
            return False
        
        if self.get('database.type') not in ['sqlite', 'postgresql']:
            logger.error("Database type must be 'sqlite' or 'postgresql'")
            return False
        
        return True
