"""
Скрипт установки и управления Windows Service
"""
import sys
import os
import win32serviceutil
import win32service
import win32api

# Добавляем путь к сервису
SERVICE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SERVICE_PATH)

from service import PrintService


def install_service():
    """Установка сервиса"""
    try:
        print("Установка Print Service...")
        
        # Собираем команду установки
        module_file = os.path.join(SERVICE_PATH, 'service.py')
        
        win32serviceutil.InstallService(
            PrintService._svc_reg_class_,
            PrintService._svc_name_,
            PrintService._svc_display_name_,
            description=PrintService._svc_description_,
            startType=win32service.SERVICE_AUTO_START,  # Автозапуск
            exeName=f'{sys.executable} "{module_file}"'
        )
        
        print(f"✓ Сервис '{PrintService._svc_display_name_}' успешно установлен")
        print(f"  Имя сервиса: {PrintService._svc_name_}")
        print(f"  Тип запуска: Автоматический")
        print("")
        print("Для запуска сервиса выполните:")
        print(f"  python install_service.py start")
        
    except Exception as e:
        print(f"✗ Ошибка установки сервиса: {e}")
        return False
    
    return True


def remove_service():
    """Удаление сервиса"""
    try:
        print("Удаление Print Service...")
        
        # Останавливаем сервис если запущен
        try:
            win32serviceutil.StopService(PrintService._svc_name_)
            print("  Сервис остановлен")
        except:
            pass
        
        # Удаляем сервис
        win32serviceutil.RemoveService(PrintService._svc_name_)
        
        print(f"✓ Сервис '{PrintService._svc_display_name_}' успешно удалён")
        
    except Exception as e:
        print(f"✗ Ошибка удаления сервиса: {e}")
        return False
    
    return True


def start_service():
    """Запуск сервиса"""
    try:
        print("Запуск Print Service...")
        win32serviceutil.StartService(PrintService._svc_name_)
        print(f"✓ Сервис '{PrintService._svc_display_name_}' запущен")
        print_service_info()
        
    except Exception as e:
        print(f"✗ Ошибка запуска сервиса: {e}")
        return False
    
    return True


def stop_service():
    """Остановка сервиса"""
    try:
        print("Остановка Print Service...")
        win32serviceutil.StopService(PrintService._svc_name_)
        print(f"✓ Сервис '{PrintService._svc_display_name_}' остановлен")
        
    except Exception as e:
        print(f"✗ Ошибка остановки сервиса: {e}")
        return False
    
    return True


def restart_service():
    """Перезапуск сервиса"""
    try:
        print("Перезапуск Print Service...")
        win32serviceutil.RestartService(PrintService._svc_name_)
        print(f"✓ Сервис '{PrintService._svc_display_name_}' перезапущен")
        print_service_info()
        
    except Exception as e:
        print(f"✗ Ошибка перезапуска сервиса: {e}")
        return False
    
    return True


def get_service_status():
    """Получение статуса сервиса"""
    try:
        status = win32serviceutil.QueryServiceStatus(PrintService._svc_name_)
        return status[1]  # Текущий статус
    except:
        return None


def print_service_info():
    """Вывод информации о сервисе"""
    print("")
    print("Информация о сервисе:")
    print("  API доступен по адресу: http://127.0.0.1:8101")
    print("  Логи: ./logs/print_service.log")


def print_status():
    """Вывод статуса сервиса"""
    status_map = {
        win32service.SERVICE_STOPPED: "Остановлен",
        win32service.SERVICE_START_PENDING: "Запускается",
        win32service.SERVICE_STOP_PENDING: "Останавливается",
        win32service.SERVICE_RUNNING: "Запущен",
        win32service.SERVICE_CONTINUE_PENDING: "Возобновляется",
        win32service.SERVICE_PAUSE_PENDING: "Приостанавливается",
        win32service.SERVICE_PAUSED: "Приостановлен"
    }
    
    status = get_service_status()
    
    if status is None:
        print(f"Сервис '{PrintService._svc_display_name_}' не установлен")
    else:
        status_text = status_map.get(status, f"Неизвестный статус ({status})")
        print(f"Сервис '{PrintService._svc_display_name_}': {status_text}")
        
        if status == win32service.SERVICE_RUNNING:
            print_service_info()


def print_usage():
    """Вывод справки"""
    print(f"""
Управление Windows Service для Print Service

Использование:
  python install_service.py [команда]

Команды:
  install   - Установить сервис
  remove    - Удалить сервис
  start     - Запустить сервис
  stop      - Остановить сервис
  restart   - Перезапустить сервис
  status    - Показать статус сервиса
  
Примеры:
  python install_service.py install
  python install_service.py start
  python install_service.py status
  
Примечание:
  Требуются права администратора для установки/удаления сервиса
""")


def main():
    """Главная функция"""
    # Проверяем права администратора для некоторых команд
    admin_commands = ['install', 'remove']
    
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command = sys.argv[1].lower()
    
    # Проверяем права администратора
    if command in admin_commands:
        try:
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                print("✗ Эта команда требует прав администратора")
                print("  Запустите cmd от имени администратора")
                return
        except:
            pass
    
    # Выполняем команду
    if command == 'install':
        install_service()
    elif command == 'remove':
        remove_service()
    elif command == 'start':
        start_service()
    elif command == 'stop':
        stop_service()
    elif command == 'restart':
        restart_service()
    elif command == 'status':
        print_status()
    else:
        print(f"✗ Неизвестная команда: {command}")
        print_usage()


if __name__ == '__main__':
    main()
