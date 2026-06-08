import logging
import sys

# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def setup_logger(name: str) -> logging.Logger:
    """Sets up and returns a configured logger."""
    logger = logging.getLogger(name)
    
    # Only configure if it doesn't already have handlers to avoid duplicates
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler (Render captures standard output automatically)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(LOG_FORMAT)
        console_handler.setFormatter(console_formatter)

        logger.addHandler(console_handler)

    return logger
