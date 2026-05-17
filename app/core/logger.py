import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "streamgate.log"


def setup_logger():
    """
    初始化 StreamGate 日志。

    日志输出到两个地方：
    1. 控制台：方便开发调试
    2. logs/streamgate.log：方便后续排查问题
    """

    # 清除 loguru 默认 logger
    logger.remove()

    # 控制台日志
    logger.add(
        sys.stdout,
        level="INFO",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    # 文件日志
    logger.add(
        LOG_FILE,
        level="INFO",
        rotation="100 MB",
        retention="14 days",
        encoding="utf-8",
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    logger.info(f"{settings.APP_NAME} logger initialized")
    logger.info(f"log file: {LOG_FILE.resolve()}")

    return logger


app_logger = setup_logger()