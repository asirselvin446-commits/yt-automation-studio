import logging
import sys
from pathlib import Path

# Create logs directory
LOGS_DIR = Path("./logs").resolve()
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """Create a structured logger with both console and file handlers."""
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler = logging.FileHandler(LOGS_DIR / log_file, encoding="utf-8")
    handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        logger.addHandler(handler)
        logger.addHandler(console_handler)
    return logger


# Specialized domain loggers
system_logger = setup_logger("system", "system.log")
agent_logger = setup_logger("agent", "agent.log")
ai_logger = setup_logger("ai", "ai.log")
upload_logger = setup_logger("upload", "upload.log")
