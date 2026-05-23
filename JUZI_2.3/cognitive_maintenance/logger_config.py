import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
           level="INFO", colorize=True)
logger.add("logs/maintenance_{time:YYYY-MM-DD}.log", rotation="1 day", retention="30 days", level="DEBUG")