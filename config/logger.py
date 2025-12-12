"""
로깅 설정
"""
from loguru import logger
import sys
from pathlib import Path

# 로그 디렉토리 생성
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# 기본 로거 제거
logger.remove()

# 콘솔 출력 (INFO 레벨 이상)
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

# 파일 출력 (DEBUG 레벨 이상, 로테이션 설정)
logger.add(
    LOGS_DIR / "app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="10 MB",  # 10MB마다 새 파일
    retention="7 days",  # 7일간 보관
    compression="zip"  # 압축
)

# 에러 전용 로그 파일
logger.add(
    LOGS_DIR / "error.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)

def get_logger(name: str):
    """
    모듈별 로거 생성

    Args:
        name: 모듈 이름

    Returns:
        logger: 설정된 로거
    """
    return logger.bind(name=name)
