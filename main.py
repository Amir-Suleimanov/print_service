"""
Главный модуль сервиса печати
Может работать как в режиме отладки (консоль), так и из Windows Service
"""
import sys
import signal
from waitress import serve

from api.routes import create_app
from utils.logger import setup_logger, get_logger


# Глобальные переменные
app = None
is_running = True
HOST = "127.0.0.1"
PORT = 8101


def setup():
    """Инициализация приложения"""
    global app

    # Настраиваем логирование
    setup_logger("INFO")
    logger = get_logger()

    logger.info("Запуск Print Service")

    # Создаём Flask приложение
    app = create_app()

    return logger


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global is_running
    logger = get_logger()
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    is_running = False
    shutdown()


def shutdown():
    """Корректное завершение работы"""
    logger = get_logger()
    
    try:
        logger.info("Сервис остановлен")
        exit()
    except Exception as e:
        logger.error(f"Ошибка при завершении работы: {e}")


def run_server():
    """Запуск сервера"""
    logger = get_logger()

    try:
        logger.info(f"Запуск сервера на {HOST}:{PORT}")

        # Используем Waitress для production
        serve(
            app,
            host=HOST,
            port=PORT,
            threads=4,
            _quiet=False
        )

    except KeyboardInterrupt:
        logger.info("Остановка Print Service")
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
    logger = setup()
    
    # Запуск сервера
    try:
        run_server()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
