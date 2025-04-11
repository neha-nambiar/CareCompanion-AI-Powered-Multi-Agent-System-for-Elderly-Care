"""
Logging utilities for the CareCompanion system.
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from utils.config import config


def setup_logger(name: str, log_file: Optional[str] = None, level: Optional[str] = None) -> logging.Logger:
    """
    Set up and configure a logger.
    
    Args:
        name: Name of the logger
        log_file: Optional file path for log output
        level: Optional log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Get log level from config if not specified
    if level is None:
        level = config.get_log_level()
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(numeric_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # If log file specified, add file handler
    if log_file:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.dirname(log_file)
        if logs_dir and not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    return logger


# Create the system logger
system_logger = setup_logger(
    'system',
    log_file=f"logs/system_{datetime.now().strftime('%Y%m%d')}.log"
)
