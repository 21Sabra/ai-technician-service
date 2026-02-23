import logging
import sys
from pythonjsonlogger import jsonlogger
from config import settings


def setup_logger():
    """Setup application logger"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.ENVIRONMENT == 'production':
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger