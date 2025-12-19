import logging
import sys

def setup_logging():
    """
    Sets up logging configuration for the application.

    Configures logging with INFO level, a standard format, and outputs logs
    immediately to both the console and a file (`AI-Review-Rating.log`).
    """
    logger = logging.getLogger("AI-Review-Rating")
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler (flush immediately)
        file_handler = logging.FileHandler("AI-Review-Rating.log", mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        file_handler.terminator = "\n"  # make sure line ends properly

        # Console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

        # Ensure logs flush immediately
        for handler in logger.handlers:
            handler.flush = lambda: handler.stream.flush()

    return logger

logger = setup_logging()