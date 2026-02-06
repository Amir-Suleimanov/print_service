"""
Главный модуль сервиса печати
Может работать как в режиме отладки (консоль), так и из Windows Service
"""
import sys
import signal
from waitress import serve

from api.routes import create_app
from config import get_config
from utils.logger import setup_logger, get_logger
from services.queue import get_print_queue


# Глобальные переменные
app = None
print_queue = None
is_running = True


def setup():
    """Инициализация приложения"""
    global app, print_queue
    
    # Загружаем конфигурацию
    config = get_config()
    
    # Настраиваем логирование
    setup_logger(config.log_level)
    logger = get_logger()
    
    logger.info("=" * 60)
    logger.info("Запуск Print Service")
    logger.info(f"Хост: {config.host}:{config.port}")
    logger.info(f"Уровень логирования: {config.log_level}")
    logger.info("=" * 60)
    
    # Создаём Flask приложение
    app = create_app()
    print_queue = get_print_queue()
    
    return config, logger


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global is_running
    logger = get_logger()
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    is_running = False
    shutdown()


def shutdown():
    """Корректное завершение работы"""
    global print_queue
    logger = get_logger()
    
    try:
        if print_queue:
            logger.info("Остановка обработки очереди...")
            print_queue.stop_processing()
        
        logger.info("Сервис остановлен")
        exit()
    except Exception as e:
        logger.error(f"Ошибка при завершении работы: {e}")


def run_server(config):
    """Запуск сервера"""
    logger = get_logger()
    
    try:
        logger.info(f"Запуск сервера на {config.host}:{config.port}")
        
        # Используем Waitress для production
        serve(
            app,
            host=config.host,
            port=config.port,
            threads=4,
            _quiet=False
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания от пользователя")
    except Exception as e:
        logger.error(f"Ошибка при запуске сервера: {e}")
        raise
    finally:
        shutdown()


def main():
    """Главная функция"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Инициализация
    config, logger = setup()
    
    # Запуск сервера
    try:
        run_server(config)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
