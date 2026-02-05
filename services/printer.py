"""
Модуль работы с принтерами Windows
"""
import win32print
import win32ui
import win32con
from PIL import Image, ImageWin
from typing import List, Dict, Optional
import os

from utils.logger import get_logger

logger = get_logger()


class PrinterService:
    """Класс для работы с Windows принтерами"""
    
    @staticmethod
    def get_printers() -> List[Dict[str, str]]:
        """
        Получение списка доступных принтеров
        
        Returns:
            Список принтеров с информацией
        """
        try:
            printers = []
            # Получаем список всех принтеров
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            
            for printer in printer_list:
                printer_info = {
                    'name': printer[2],  # Имя принтера
                    'status': 'Ready',  # Упрощенный статус
                    'is_default': printer[2] == win32print.GetDefaultPrinter()
                }
                printers.append(printer_info)
            
            logger.info(f"Найдено принтеров: {len(printers)}")
            return printers
            
        except Exception as e:
            logger.error(f"Ошибка получения списка принтеров: {e}")
            return []
    
    @staticmethod
    def get_default_printer() -> Optional[str]:
        """
        Получение принтера по умолчанию
        
        Returns:
            Имя принтера по умолчанию или None
        """
        try:
            default_printer = win32print.GetDefaultPrinter()
            logger.debug(f"Принтер по умолчанию: {default_printer}")
            return default_printer
        except Exception as e:
            logger.error(f"Ошибка получения принтера по умолчанию: {e}")
            return None
    
    @staticmethod
    def printer_exists(printer_name: str) -> bool:
        """
        Проверка существования принтера
        
        Args:
            printer_name: Имя принтера
            
        Returns:
            True если принтер существует
        """
        printers = PrinterService.get_printers()
        return any(p['name'] == printer_name for p in printers)
    
    @staticmethod
    def print_pdf(file_path: str, printer_name: Optional[str] = None, options: Optional[Dict] = None) -> str:
        """
        Печать PDF файла
        
        Args:
            file_path: Путь к PDF файлу
            printer_name: Имя принтера (опционально)
            options: Опции печати
            
        Returns:
            ID задания печати
        """
        try:
            # Определяем принтер
            if not printer_name:
                printer_name = PrinterService.get_default_printer()
            
            if not printer_name:
                raise ValueError("Не указан принтер и отсутствует принтер по умолчанию")
            
            # Проверяем существование принтера
            if not PrinterService.printer_exists(printer_name):
                raise ValueError(f"Принтер не найден: {printer_name}")
            
            logger.info(f"Отправка PDF на печать: {file_path} -> {printer_name}")
            
            # Используем win32api для печати PDF
            # Это самый простой способ для PDF - отправляем файл напрямую на принтер
            import win32api
            
            # Для PDF используем прямую печать через ShellExecute
            win32api.ShellExecute(
                0,
                "print",
                file_path,
                f'/d:"{printer_name}"',
                ".",
                0
            )
            
            # Генерируем ID задания (упрощённо)
            import uuid
            job_id = str(uuid.uuid4())
            
            logger.info(f"PDF отправлен на печать. Job ID: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Ошибка печати PDF: {e}")
            raise
    
    @staticmethod
    def print_image(file_path: str, printer_name: Optional[str] = None, options: Optional[Dict] = None) -> str:
        """
        Печать изображения
        
        Args:
            file_path: Путь к изображению
            printer_name: Имя принтера (опционально)
            options: Опции печати
            
        Returns:
            ID задания печати
        """
        try:
            # Определяем принтер
            if not printer_name:
                printer_name = PrinterService.get_default_printer()
            
            if not printer_name:
                raise ValueError("Не указан принтер и отсутствует принтер по умолчанию")
            
            # Проверяем существование принтера
            if not PrinterService.printer_exists(printer_name):
                raise ValueError(f"Принтер не найден: {printer_name}")
            
            logger.info(f"Отправка изображения на печать: {file_path} -> {printer_name}")
            
            # Открываем изображение
            image = Image.open(file_path)
            
            # Создаём контекст устройства принтера
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)
            
            # Получаем размеры печатной области
            printable_area = hdc.GetDeviceCaps(win32con.HORZRES), hdc.GetDeviceCaps(win32con.VERTRES)
            printer_size = hdc.GetDeviceCaps(win32con.HORZSIZE), hdc.GetDeviceCaps(win32con.VERTSIZE)
            
            # Начинаем задание печати
            hdc.StartDoc(os.path.basename(file_path))
            hdc.StartPage()
            
            # Вычисляем масштаб для вписывания изображения
            image_width, image_height = image.size
            scale_x = printable_area[0] / image_width
            scale_y = printable_area[1] / image_height
            scale = min(scale_x, scale_y)
            
            # Новые размеры изображения
            new_width = int(image_width * scale)
            new_height = int(image_height * scale)
            
            # Центрируем изображение
            x = (printable_area[0] - new_width) // 2
            y = (printable_area[1] - new_height) // 2
            
            # Печатаем изображение
            dib = ImageWin.Dib(image)
            dib.draw(hdc.GetHandleOutput(), (x, y, x + new_width, y + new_height))
            
            # Завершаем печать
            hdc.EndPage()
            hdc.EndDoc()
            hdc.DeleteDC()
            
            # Генерируем ID задания
            import uuid
            job_id = str(uuid.uuid4())
            
            logger.info(f"Изображение отправлено на печать. Job ID: {job_id}")
            return job_id
            
        except Exception as e:
            logger.error(f"Ошибка печати изображения: {e}")
            raise
    
    @staticmethod
    def print_file(file_path: str, file_format: str, printer_name: Optional[str] = None, 
                   options: Optional[Dict] = None, copies: int = 1) -> str:
        """
        Печать файла (универсальный метод)
        
        Args:
            file_path: Путь к файлу
            file_format: Формат файла (pdf, image, text)
            printer_name: Имя принтера
            options: Опции печати
            copies: Количество копий
            
        Returns:
            ID задания печати
        """
        try:
            # Определяем принтер
            if not printer_name:
                printer_name = PrinterService.get_default_printer()
            
            # Печатаем несколько копий если требуется
            job_ids = []
            for i in range(copies):
                if file_format == 'pdf':
                    job_id = PrinterService.print_pdf(file_path, printer_name, options)
                elif file_format == 'image':
                    job_id = PrinterService.print_image(file_path, printer_name, options)
                else:
                    # Для остальных форматов используем PDF метод
                    logger.warning(f"Формат {file_format} не поддерживается напрямую, используем прямую печать")
                    job_id = PrinterService.print_pdf(file_path, printer_name, options)
                
                job_ids.append(job_id)
                
                if copies > 1:
                    logger.info(f"Отправлена копия {i+1}/{copies}")
            
            # Возвращаем ID первого задания (или можно вернуть список)
            return job_ids[0] if job_ids else None
            
        except Exception as e:
            logger.error(f"Ошибка печати файла: {e}")
            raise
    
    @staticmethod
    def cancel_job(job_id: str) -> bool:
        """
        Отмена задания печати
        
        Args:
            job_id: ID задания
            
        Returns:
            True если успешно отменено
        """
        # Упрощённая реализация
        # В реальности нужно хранить соответствие между нашими UUID и реальными job ID Windows
        logger.warning(f"Отмена задания {job_id} не реализована полностью")
        return False
