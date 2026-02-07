"""
Модуль настройки логирования для сервиса печати
"""
from pathlib import Path
from loguru import logger


LIFECYCLE_INFO_MARKERS = (
    "Запуск Print Service",
    "Запуск сервера на",
    "Windows Service запущен",
    "Получена команда остановки сервиса",
    "Получен сигнал",
    "Остановка обработки очереди",
    "Сервис остановлен",
    "Сервис завершён",
)


def _log_filter(record: dict) -> bool:
    """
    Оставляем только:
    - ошибки (ERROR/CRITICAL);
    - служебные INFO о запуске/завершении приложения.
    """
    level_name = record["level"].name
    if level_name in {"ERROR", "CRITICAL"}:
        return True

    if level_name == "INFO":
        message = record["message"]
        return any(marker in message for marker in LIFECYCLE_INFO_MARKERS)

    return False


def setup_logger(log_level: str = "INFO", log_file: str = "./logs/{time:YYYY-MM-DD}.log"):
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
    
    # Добавляем вывод в файл:
    # отдельный файл на каждый день с именем в формате YYYY-MM-DD.log
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="00:00",  # Переключать файл в полночь
        retention="7 days",  # Хранить логи 7 дней
        encoding="utf-8",
        filter=_log_filter,
    )
    
    return logger


def get_logger():
    """
    Получение экземпляра логгера
    
    Returns:
        Логгер
    """
    return logger
