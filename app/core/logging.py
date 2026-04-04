import logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    # suppress uvicorn's own per-request access logs — our middleware handles it
    "loggers": {
        "uvicorn.access": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}


def setup_logging(level: str = "INFO") -> None:
    LOGGING_CONFIG["root"]["level"] = level.upper()
    logging.config.dictConfig(LOGGING_CONFIG)
