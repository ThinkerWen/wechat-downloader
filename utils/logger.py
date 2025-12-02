"""
统一日志配置模块
"""
import os
import sys
from datetime import datetime

from loguru import logger

from utils.config import config


class LoggerManager:
    _instance = None
    _initialized = False

    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._setup_logger()
        self._initialized = True

    @staticmethod
    def _setup_logger():
        log_dir = config.log_dir
        os.makedirs(log_dir, exist_ok=True)
        logger.remove()

        logger.add(
            sink=sys.stderr,
            format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level="INFO",
            colorize=True,
            enqueue=False
        )

        current_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.add(
            sink=os.path.join(log_dir, f"{current_date}.log"),
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            retention="7 days",
            encoding="utf-8",
            enqueue=True
        )

    @staticmethod
    def get_logger():
        return logger


logger_manager = LoggerManager()
__all__ = ['LoggerManager', 'logger_manager', 'logger']
