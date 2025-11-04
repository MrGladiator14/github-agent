"""
Logging configuration for the GitHub MCP project.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

# Default log format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_LEVEL = logging.DEBUG

# Log file configuration
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "github_mcp.log"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5


def setup_logger(
    name: str,
    log_level: int = DEFAULT_LEVEL,
    log_file: Optional[Path] = None,
    log_format: str = DEFAULT_LOG_FORMAT,
    console: bool = True,
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.

    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (default: logging.DEBUG)
        log_file: Path to log file (default: logs/github_mcp.log)
        log_format: Log message format
        console: Whether to log to console (default: True)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    logger.setLevel(log_level)
    logger.propagate = False  # Prevent propagation to root logger

    # Create formatter
    formatter = logging.Formatter(log_format)

    # Set default log file if not provided
    if log_file is None:
        log_file = LOG_FILE.absolute()
    else:
        log_file = Path(log_file).absolute()

    try:
        # Ensure the logs directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file handler with error handling
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_file), 
            maxBytes=LOG_MAX_BYTES, 
            backupCount=LOG_BACKUP_COUNT, 
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # Add file handler
        logger.addHandler(file_handler)
        
        # Test file handler
        logger.debug("Debug message - this should appear in the log")
        logger.info(f"Initialized logger for {name}. Log level: {logging.getLevelName(log_level)}")
        
    except Exception as e:
        print(f"Failed to set up file logging to {log_file}: {e}", file=sys.stderr)
        print("Falling back to console logging only.", file=sys.stderr)
        console = True  # Ensure console logging is enabled if file logging fails

    # Create console handler if requested
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Ensure the root logger doesn't propagate to console
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(logging.NullHandler())

    return logger


# Create default logger
# logger = setup_logger(__name__)

# def get_logger(name: str = None) -> logging.Logger:
#     """
#     Get a logger with the given name, or the root logger if no name is provided.
    
#     Args:
#         name: Logger name (usually __name__)
        
#     Returns:
#         Configured logger instance
#     """
#     if name is None:
#         return logger
#     return logging.getLogger(name)
