# logger_config.py
import sys
from loguru import logger

# 移除默认 handler
logger.remove()

# 控制台输出（纯文本格式，不带颜色标记）
logger.add(
    sys.stderr,
    format="{time:HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
    level="INFO"
)

# JSON 日志文件（每天轮转，保留30天）
logger.add(
    "logs/enhancer_{time:YYYY-MM-DD}.json",
    format="{time} | {level} | {message}",
    serialize=True,
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)

# 性能监控专用日志（单独文件）
logger.add(
    "logs/performance.json",
    format="{time} | {message}",
    serialize=True,
    rotation="100 MB",
    filter=lambda record: record["extra"].get("type") == "performance"
)