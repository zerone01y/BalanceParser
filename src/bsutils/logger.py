import sys
from pathlib import Path

from loguru import logger


def info_only(record):
    return record["level"].name == "INFO"


INFO_SUCCESS_LEVELS = {"INFO", "SUCCESS"}
WARNING_LEVEL_NO = logger.level("WARNING").no
SUCCESS_LEVEL = logger.level("SUCCESS")
logger.level("SUCCESS", color="<green>", icon=SUCCESS_LEVEL.icon)
LEVEL_MESSAGE_FORMAT = "<level><bold>{level}</bold> | {message}</level>"


def info_success_only(record):
    return record["level"].name in INFO_SUCCESS_LEVELS


def warning_and_above(record):
    return record["level"].no >= WARNING_LEVEL_NO


def debug_only(record):
    return record["level"].name == "DEBUG"


def configure_logger(debug_mode: bool = False):
    """
    Configure global Loguru logger according to mode.

    debug_mode=True  -> log INFO to statement.log and DEBUG+ to stdout.
    debug_mode=False -> disable logging sinks.
    """
    logger.remove()
    log_path = Path("statement.log")

    if debug_mode:
        logger.add(log_path, filter=info_only, format="{message}")
        logger.add(sys.stdout, filter=debug_only, level="DEBUG")
        logger.add(
            sys.stdout,
            filter=info_success_only,
            format=LEVEL_MESSAGE_FORMAT,
        )
        logger.add(sys.stdout, filter=warning_and_above, level="WARNING")
    else:
        logger.add(
            sys.stdout,
            filter=info_success_only,
            level="SUCCESS",
            format=LEVEL_MESSAGE_FORMAT,
        )
        logger.add(sys.stdout, filter=warning_and_above, level="WARNING")


# Default configuration: silent unless debug mode is explicitly enabled.
configure_logger(False)
