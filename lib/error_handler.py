import logging
from logging import handlers
import os
import traceback
from datetime import datetime
from typing import Optional, Union, Dict, Any

# this was created by AI.
# I honestly have no clue how it works.
# And it is going to bite me in the ass one day.

class ErrorHandler:
    """
    A class to handle error logging with customizable formatting and file output.
    Specifically focused on error logging and debugging issues.
    """
    def __init__(
        self,
        log_file: str = "soundcloud_downloader.log",
        log_dir: str = "logs",
        log_level: int = logging.INFO,
        format_string: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB default
        backup_count: int = 3
    ):
        """
        Initialize the error handler.
        
        Args:
            log_file (str): Name of the log file
            log_dir (str): Directory to store log files
            log_level (int): Logging level (default: logging.ERROR)
            format_string (str, optional): Custom format string for log messages
            max_file_size (int): Maximum size of log file before rotation in bytes
            backup_count (int): Number of backup files to keep
        """
        self.log_file = log_file
        self.log_dir = log_dir
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.log_path = os.path.join(log_dir, log_file)
        
        # Clear existing log file by opening it in write mode and closing immediately
        with open(self.log_path, 'w') as f:
            pass
        
        # Set up logger
        self.logger = logging.getLogger('SoundCloudDownloader')
        # Prevent duplicate logs by clearing existing handlers
        self.logger.handlers = []
        self.logger.setLevel(log_level)
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
        
        # Default format string if none provided - removed timestamp from message since it's in the formatter
        if format_string is None:
            format_string = '[%(asctime)s] %(levelname)s: %(message)s'
        
        # Create formatter
        formatter = logging.Formatter(format_string)
        
        # Set up file handler with 'w' mode instead of 'a' mode
        file_handler = handlers.RotatingFileHandler(
            self.log_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            mode='w'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.logger.addHandler(file_handler)
    
    def log_error(
        self,
        error: Union[Exception, str],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with optional context information.
        
        Args:
            error: The error to log (can be an Exception or string)
            context: Optional dictionary of contextual information
        """
        if isinstance(error, Exception):
            error_message = str(error)
            error_traceback = ''.join(traceback.format_tb(error.__traceback__))
        else:
            error_message = str(error)
            error_traceback = ''
        
        # Build the log message
        log_parts = [f"Error: {error_message}"]
        
        if error_traceback:
            log_parts.append(f"Traceback:\n{error_traceback}")
            
        if context:
            context_str = '\n'.join(f"{k}: {v}" for k, v in context.items())
            log_parts.append(f"Context:\n{context_str}")
        
        # Join all parts with newlines
        final_message = '\n'.join(log_parts)
        
        # Log the message
        self.logger.error(final_message)
    
    def log_info(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Convenience method to log info messages."""
        if context:
            context_str = '\n'.join(f"{k}: {v}" for k, v in context.items())
            message = f"{message}\nContext:\n{context_str}"
        self.logger.info(message)
    
    def log_warning(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Convenience method to log warning messages."""
        if context:
            context_str = '\n'.join(f"{k}: {v}" for k, v in context.items())
            message = f"{message}\nContext:\n{context_str}"
        self.logger.warning(message)
    
    def log_critical(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Convenience method to log critical messages."""
        if context:
            context_str = '\n'.join(f"{k}: {v}" for k, v in context.items())
            message = f"{message}\nContext:\n{context_str}"
        self.logger.critical(message)
    
    def get_logs(self, n_lines: int = 100) -> list[str]:
        """
        Retrieve the last n lines from the log file.
        
        Args:
            n_lines: Number of lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
                return lines[-n_lines:]
        except FileNotFoundError:
            return []

# Create a default instance
default_handler = ErrorHandler()

# Only provide error logging function since this is an error handler
def log_error(error: Union[Exception, str], context: Optional[Dict[str, Any]] = None) -> None:
    """Log an error with optional context information."""
    default_handler.log_error(error, context=context)

def log_info(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    default_handler.log_info(message, context=context)

def log_warning(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    default_handler.log_warning(message, context=context)

def log_critical(message: str, context: Optional[Dict[str, Any]] = None) -> None:
    default_handler.log_critical(message, context=context)

def get_logs(n_lines: int = 100) -> list[str]:
    return default_handler.get_logs(n_lines)