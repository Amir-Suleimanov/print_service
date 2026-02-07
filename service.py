"""
Windows Service wrapper для Print Service
"""
import sys
import os
import servicemanager
import win32serviceutil
import win32service
import win32event
import threading

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

from main import setup, shutdown
from waitress import serve
from utils.logger import get_logger


class PrintService(win32serviceutil.ServiceFramework):
    """Windows Service для сервиса печати"""
    
    _svc_name_ = "PrintService"
    _svc_display_name_ = "Print Service"
    _svc_description_ = "Сервис печати документов через REST API"
    
    def __init__(self, args):
        """Инициализация сервиса"""
        win32serviceutil.ServiceFramework.__init__(self, args)
        
        # Событие для остановки сервиса
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        
        # Флаг работы
        self.is_running = True
        
        # Flask приложение
        self.app = None
        self.server_thread = None
    
    def SvcStop(self):
        """Остановка сервиса"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        # Логируем остановку
        try:
            logger = get_logger()
            logger.info("Получена команда остановки сервиса")
        except:
            pass
        
        # Устанавливаем флаг остановки
        self.is_running = False
        win32event.SetEvent(self.stop_event)
        
        # Останавливаем приложение
        shutdown()
    
    def SvcDoRun(self):
        """Запуск сервиса"""
        try:
            # Логируем запуск
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Инициализация
            logger = setup()
            logger.info("Windows Service запущен")
            
            # Импортируем приложение
            from api.routes import create_app
            self.app = create_app()
            
            # Запускаем сервер в отдельном потоке
            self.server_thread = threading.Thread(
                target=self._run_server,
                daemon=False
            )
            self.server_thread.start()
            
            logger.info("Сервер запущен на 127.0.0.1:8101")
            
            # Ждём сигнала остановки
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            
            logger.info("Сервис завершён")
            
        except Exception as e:
            # Логируем ошибку
            servicemanager.LogErrorMsg(f"Ошибка в сервисе: {str(e)}")
            
            try:
                logger = get_logger()
                logger.error(f"Критическая ошибка сервиса: {e}")
            except:
                pass
    
    def _run_server(self):
        """Запуск Flask сервера в потоке"""
        try:
            logger = get_logger()
            logger.info("Запуск Waitress сервера...")
            
            # Запускаем Waitress
            serve(
                self.app,
                host="127.0.0.1",
                port=8101,
                threads=4,
                _quiet=False
            )
            
        except Exception as e:
            try:
                logger = get_logger()
                logger.error(f"Ошибка сервера: {e}")
            except:
                pass


if __name__ == '__main__':
    """
    Точка входа для управления сервисом
    Используется через pywin32
    """
    if len(sys.argv) == 1:
        # Запуск как сервис
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PrintService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Установка/удаление/управление сервисом
        win32serviceutil.HandleCommandLine(PrintService)
