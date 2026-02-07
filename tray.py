"""
Tray-приложение для Print Service
Запускает сервер и показывает иконку в области уведомлений
"""
import threading
import sys
import os
import winreg
import time

import pystray
from PIL import Image

# Перенаправление вывода когда нет консоли (exe без console)
if getattr(sys, 'frozen', False):
    log_dir = os.path.join(os.path.dirname(sys.executable), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{time.strftime('%Y-%m-%d')}.log")
    if not os.path.exists(log_file):
        open(log_file, 'a', encoding='utf-8').close()
    sys.stdout = open(log_file, 'a', encoding='utf-8', buffering=1)
    sys.stderr = sys.stdout
# ============================

# Определяем пути
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Настройки
APP_NAME = "PrintService"
REGISTRY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_APPROVED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
HOST = "127.0.0.1"
PORT = 8101


def log_error(message: str):
    """Логировать ошибку в основной лог-файл."""
    try:
        from utils.logger import setup_logger, get_logger
        setup_logger("INFO")
        get_logger().error(message)
    except Exception:
        pass


class PrintServiceTray:
    def __init__(self):
        self.icon = None
        self.server_thread = None
        self.server_running = False
    
    def load_icon(self):
        """Загрузить иконку из файла"""
        if os.path.exists(ICON_PATH):
            try:
                return Image.open(ICON_PATH)
            except Exception as e:
                log_error(f"Ошибка загрузки иконки: {e}")
        
        # Fallback
        from PIL import ImageDraw
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8, 8, 56, 56], fill=(0, 120, 215), outline=(255, 255, 255))
        return img
    
    def check_server_health(self):
        """Проверить статус сервера"""
        try:
            import urllib.request
            import urllib.error
            
            url = f"http://{HOST}:{PORT}/health"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    return True, response.read().decode('utf-8')
        except urllib.error.URLError as e:
            return False, f"Сервер недоступен: {e.reason}"
        except Exception as e:
            return False, f"Ошибка: {e}"
        
        return False, "Неизвестная ошибка"
    
    def start_server(self):
        """Запуск сервера в отдельном потоке"""
        if self.server_running:
            return
        
        def run():
            try:
                from api.routes import create_app
                from services.queue import get_print_queue
                from utils.logger import setup_logger, get_logger
                from waitress import serve
                
                setup_logger("INFO")
                logger = get_logger()
                
                app = create_app()
                
                self.server_running = True
                logger.info(f"Запуск сервера на {HOST}:{PORT}")
                
                serve(app, host=HOST, port=PORT, threads=4, _quiet=True)
                
            except Exception as e:
                log_error(f"Server error: {e}")
                self.server_running = False
        
        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        
        # Ждём запуска сервера
        for _ in range(10):
            time.sleep(0.5)
            ok, _ = self.check_server_health()
            if ok:
                self.notify("Сервер запущен", f"http://{HOST}:{PORT}")
                return
        
        self.notify("Предупреждение", "Сервер запускается...")
    
    def notify(self, title, message=""):
        """Показать уведомление"""
        if self.icon:
            try:
                self.icon.notify(message, title)
            except:
                pass
    
    # === Обработчики меню ===
    
    def on_status(self, icon, item):
        """Показать статус"""
        ok, data = self.check_server_health()
        if ok:
            self.notify("✅ Статус: работает", f"http://{HOST}:{PORT}")
        else:
            self.notify("❌ Статус: не отвечает", str(data))
    
    def on_autostart_toggle(self, icon, item):
        """Переключить автозапуск"""
        if is_in_autostart():
            remove_from_autostart()
            self.notify("Автозапуск", "Выключен")
        else:
            add_to_autostart()
            self.notify("Автозапуск", "Включен")
    
    def on_exit(self, icon, item):
        """Выход из приложения"""
        try:
            from utils.logger import get_logger
            get_logger().info("Сервис завершён")
        except Exception:
            pass
        self.server_running = False
        icon.stop()
    
    def run(self):
        """Главный запуск"""
        # Автоматически добавляем в автозапуск при первом запуске
        if not is_in_autostart():
            add_to_autostart()
        
        # Запускаем сервер
        self.start_server()
        
        # Создаём меню
        menu = pystray.Menu(
            pystray.MenuItem("📊 Статус", self.on_status, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🚀 Автозапуск",
                self.on_autostart_toggle,
                checked=lambda item: is_in_autostart()
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Выход", self.on_exit),
        )
        
        # Создаём иконку
        self.icon = pystray.Icon(
            name="print_service",
            icon=self.load_icon(),
            title=f"Print Service - http://{HOST}:{PORT}",
            menu=menu
        )
        
        self.icon.run()


# === Автозапуск ===

def get_exe_path():
    """Получить путь к исполняемому файлу"""
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    else:
        return f'"{sys.executable}" "{os.path.abspath(__file__)}"'


def add_to_autostart():
    """Добавить в автозапуск"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            REGISTRY_KEY, 
            0, 
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_exe_path())
        winreg.CloseKey(key)
        _set_startup_approved_enabled()
        return True
    except Exception as e:
        log_error(f"Автозапуск: {e}")
        return False


def remove_from_autostart():
    """Удалить из автозапуска"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            REGISTRY_KEY, 
            0, 
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        _remove_startup_approved_value()
        return True
    except FileNotFoundError:
        _remove_startup_approved_value()
        return True
    except Exception as e:
        log_error(f"Удаление из автозапуска: {e}")
        return False


def is_in_autostart():
    """Проверить, что автозапуск добавлен и включен"""
    if not _has_run_entry():
        return False
    return _is_startup_approved_enabled()


def _has_run_entry():
    """Проверить наличие записи в HKCU\\...\\Run"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, 
            REGISTRY_KEY, 
            0, 
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def _set_startup_approved_enabled():
    """
    Для Windows 10/11 явно устанавливаем состояние Enabled в StartupApproved.
    Для Windows 7 этот ключ может не использоваться системой.
    """
    try:
        key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        # 0x02 в первом байте означает состояние "Enabled".
        enabled_data = bytes([0x02, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_BINARY, enabled_data)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log_error(f"StartupApproved enable: {e}")
        return False


def _remove_startup_approved_value():
    """Удалить значение из StartupApproved, если оно есть."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return True
    except Exception as e:
        log_error(f"StartupApproved remove: {e}")
        return False


def _is_startup_approved_enabled():
    """
    Если записи в StartupApproved нет, считаем автозапуск включенным
    (поведение Windows 7 и некоторых сценариев Windows 10).
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_APPROVED_KEY,
            0,
            winreg.KEY_READ
        )
        data, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        if isinstance(data, (bytes, bytearray)) and len(data) > 0:
            return data[0] == 0x02
        return True
    except FileNotFoundError:
        return True
    except Exception:
        return False


# === Точка входа ===

if __name__ == '__main__':
    app = PrintServiceTray()
    app.run()
