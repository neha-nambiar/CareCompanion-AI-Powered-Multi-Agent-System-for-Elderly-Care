"""
Configuration utilities for the CareCompanion system.
Handles loading and accessing configuration settings.
"""

import os
import yaml
from typing import Any, Dict, Optional, List, Union


class Config:
    """
    Configuration manager class for the CareCompanion system.
    Loads settings from YAML file and provides access methods.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the Configuration manager.
        
        Args:
            config_path: Path to the configuration YAML file
        """
        self.config_path = config_path
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.
        
        Returns:
            Dict containing configuration settings
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        
        try:
            with open(self.config_path, 'r') as config_file:
                config_data = yaml.safe_load(config_file)
            
            return config_data
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation path.
        
        Args:
            key_path: Dot-separated path to configuration value
            default: Default value to return if path not found
            
        Returns:
            Configuration value or default if not found
        """
        keys = key_path.split('.')
        value = self.config_data
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration dictionary.
        
        Returns:
            Dict containing all configuration settings
        """
        return self.config_data
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dict containing agent configuration or empty dict if not found
        """
        return self.get(f"agents.{agent_name}", {})
    
    def get_llm_model(self, agent_name: str) -> str:
        """
        Get the LLM model name for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            String containing model name or default model
        """
        model_name = self.get(f"llm.models.{agent_name}")
        if not model_name:
            model_name = self.get("llm.models.default", "Gemma-2B")
        
        return model_name
    
    def get_data_path(self) -> str:
        """
        Get the path to data directory.
        
        Returns:
            String containing path to data directory
        """
        return self.get("system.data_path", "./data/")
    
    def get_log_level(self) -> str:
        """
        Get the log level for the system.
        
        Returns:
            String containing log level
        """
        return self.get("system.log_level", "INFO")


# Create a singleton instance
config = Config()