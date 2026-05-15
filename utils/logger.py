import logging
import sys


def setup_logging(name="Surgzon", log_file="surgzon.log"):
    """
    Sets up logging configuration for the application.

    Configures logging with INFO level, a standard format, and outputs logs
    immediately to both the console and a file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.INFO)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


logger = setup_logging()
