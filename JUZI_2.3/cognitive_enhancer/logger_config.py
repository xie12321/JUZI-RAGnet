# logger_config.py
import sys
from loguru import logger

# 移除默认的 handler
logger.remove()

# 控制台输出（彩色，适合开发环境）
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True
)

# 文件输出：普通文本日志（每日轮转，保留30天）
logger.add(
    "logs/cognitive_enhancer_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} | {message}",
    rotation="1 day",
    retention="30 days",
    compression="zip",
    level="DEBUG"
)

# 文件输出：结构化 JSON 日志（便于分析，可选）
logger.add(
    "logs/cognitive_enhancer_{time:YYYY-MM-DD}.json",
    format="{time} | {level} | {message}",
    serialize=True,
    rotation="1 day",
    retention="30 days",
    level="INFO"
)

# 性能监控专用日志（单独文件，只记录性能相关）
logger.add(
    "logs/performance.json",
    format="{time} | {message}",
    serialize=True,
    rotation="100 MB",
    filter=lambda record: record["extra"].get("type") == "performance",
    level="INFO"
)

# 可选：节点执行日志单独文件
logger.add(
    "logs/nodes.log",
    format="{time:HH:mm:ss} | {level} | {message}",
    rotation="50 MB",
    filter=lambda record: record["extra"].get("node") is not None,
    level="INFO"
)