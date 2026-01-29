import sys
import os
from loguru import logger

# 移除默认的控制台输出
logger.remove()

# 自定义级别颜色，确保 INFO 显示为绿色
logger.level("INFO", color="<green>")
logger.level("DEBUG", color="<blue>")
logger.level("WARNING", color="<yellow>")
logger.level("ERROR", color="<red>")

# 配置控制台输出（带颜色，模仿 Java Spring Boot 风格）
# 格式：日期 时间.毫秒  级别(带颜色)  消息
logger.add(
    sys.stdout,
    colorize=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS}  <level>{level: <8}</level> {message}",
    level="INFO"
)

# 配置文件输出（自动按天切割，保留 7 天）
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logger.add(
    os.path.join(log_dir, "app.log"),
    rotation="00:00",
    retention="7 days",
    enqueue=True,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS}  {level: <8} {message}",
    level="INFO"
)

def log(message, level="INFO"):
    """
    分级日志输出
    :param message: 日志内容
    :param level: 日志级别 (INFO, ERROR, WARNING, DEBUG)
    """
    level = level.upper()
    if level == "INFO":
        logger.info(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    elif level == "DEBUG":
        logger.debug(message)
    else:
        logger.info(message)
