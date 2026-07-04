import structlog

from config.settings import env

LOG_LEVEL = env("LOG_LEVEL", default="INFO")
SHARED_LOG_PROCESSORS = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
]
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": SHARED_LOG_PROCESSORS,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(),
            ],
        },
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": SHARED_LOG_PROCESSORS,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        },
        "plain": {
            "()": structlog.stdlib.ProcessorFormatter,
            "foreign_pre_chain": SHARED_LOG_PROCESSORS,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=False),
            ],
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "plain",
            "level": LOG_LEVEL,
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

structlog.configure(
    processors=[
        *SHARED_LOG_PROCESSORS,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
