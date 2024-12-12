from datetime import datetime
import logging
import logging.config
import logging.handlers
from enum import IntFlag, auto
from pathlib import Path

from omegaconf import OmegaConf

from ..models.configuration import AppLogging

logger = logging.getLogger(__name__)


class AppLoggingMode(IntFlag):
    NONE = auto()
    SERVER = auto()
    CLIENT = auto()
    UI = auto()


# logging config
def configure_app_logging(mode: AppLoggingMode, config: AppLogging = None):
    # basic logging configuration
    app_logging_config = """
    app_logging:
        version: 1
        formatters:
            simple:
                format: "[%(asctime)s][%(levelname)s] %(message)s"
                datefmt: "%Y-%m-%d %H:%M:%S"
            rich:
                format: "[%(thread)s] %(message)s"
                datefmt: "%Y-%m-%d %H:%M:%S"
        handlers:
            console:
                class: rich.logging.RichHandler
                formatter: rich
                markup: False
            client:
                class: mfclib.logging.TimeStampedFileHandler
                formatter: simple
                filename: ".log/client/{0:%Y-%m-%d}/{0:%Y-%m-%dT%H-%M-%S}.log"
                encoding: utf-8
            server:
                class: mfclib.logging.TimedRotatingFileHandler
                formatter: simple
                filename: ".log/server/server.log"
                encoding: utf-8
                when: "midnight"
                interval: 1
        root:
            level: NOTSET
            handlers:
                - console
        disable_existing_loggers: false
    """
    cfg = OmegaConf.to_object(
        OmegaConf.create(app_logging_config).app_logging,
    )
    if config is not None:
        # update logging level
        cfg['root']['level'] = config.level

        # update formatters
        for key in config.formatters:
            cfg['formatters'][key] = config.formatters[key]

        # update handlers
        for key in config.handlers:
            cfg['handlers'][key] = config.handlers[key]

    # add application specific handlers to root
    match mode:
        case AppLoggingMode.SERVER:
            cfg['root']['handlers'].append('server')
        case AppLoggingMode.CLIENT:
            cfg['root']['handlers'].append('client')

    if (config is None) or not (config.disable_logging):
        logging.config.dictConfig(cfg)
        logger.info(f'Configured app logging: {str(mode)}')


class TimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    def __init__(self, filename, **kwargs):
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, **kwargs)


class TimeStampedFileHandler(logging.FileHandler):
    def __init__(self, filename, **kwargs):
        filename = filename.format(datetime.now())
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename, **kwargs)
