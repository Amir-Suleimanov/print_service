"""
Модуль настройки логирования для сервиса печати
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", log_file: str = "./logs/print_service.log"):
    """
    Настройка логирования для сервиса
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу логов
    """
    # Удаляем стандартный handler
    logger.remove()
    
    # Создаём папку для логов если не существует
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Форматирование логов
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Добавляем вывод в консоль
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Добавляем вывод в файл с ротацией
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="10 MB",  # Ротация при достижении 10 МБ
        retention="7 days",  # Хранить логи 7 дней
        compression="zip",  # Сжимать старые логи
        encoding="utf-8"
    )
    
    logger.info(f"Логирование настроено. Уровень: {log_level}, Файл: {log_file}")
    
    return logger


def get_logger():
    """
    Получение экземпляра логгера
    
    Returns:
        Логгер
    """
    return logger
