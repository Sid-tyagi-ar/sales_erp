import logging
import sys
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Prevent adding multiple handlers if logger already exists
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter(
            fmt=(
                "%(asctime)s | %(levelname)-8s | "
                "%(name)s | %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
