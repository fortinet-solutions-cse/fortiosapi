import os
import sys
import logging
import dictconfig

DEFAULT_BASE_LOGGING_LEVEL = logging.INFO
DEFAULT_VERBOSE_LOGGING_LEVEL = logging.DEBUG

LOGGER = {
    "version": 1,
    "formatters": {
        "file": {
            "format": "%(asctime)s %(levelname)s - %(message)s"
        },
        "console": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "file",
            "level": "DEBUG",
            "filename": os.path.expanduser("~/.wagon/wagon.log"),
            "maxBytes": "5000000",
            "backupCount": "20"
        },
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "console"
        }
    },
    "loggers": {
        "user": {
            "handlers": ["file", "console"]
        },
    }
}


def init(base_level=DEFAULT_BASE_LOGGING_LEVEL,
         verbose_level=DEFAULT_VERBOSE_LOGGING_LEVEL):
    """Initializes a base logger
    """
    lgr = logging.getLogger('user')
    lgr.setLevel(base_level)
    return lgr


def configure():
    """Configures the logger using the default configuration.
    """
    try:
        log_file = LOGGER['handlers']['file']['filename']
    except KeyError as ex:
        sys.exit('Failed retrieving log file path ({0}).'.format(str(ex)))
    log_dir = os.path.dirname(os.path.expanduser(log_file))
    if os.path.isfile(log_dir):
        sys.exit('File {0} exists - log directory cannot be created '
                 'there. please remove the file and try again.'.format(
                     log_dir))
    try:
        if not os.path.exists(log_dir) and not len(log_dir) == 0:
            os.makedirs(log_dir)
        dictconfig.dictConfig(LOGGER)

    except ValueError as ex:
        sys.exit('Could not configure logger.'
                 ' verify your logger config'
                 ' and permissions to write to {0} ({1})'.format(
                     log_file, str(ex)))
