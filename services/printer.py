"""
Модуль работы с принтерами Windows
"""
import os
import uuid
import win32print
import win32ui
import win32con
from PIL import Image, ImageWin
from typing import List, Dict, Optional

from utils.logger import get_logger

logger = get_logger()


class PrinterService:
    """Класс для работы с Windows принтерами"""

    @staticmethod
    def get_printers() -> List[Dict[str, str]]:
        """Получение списка принтеров"""
        try:
            printers = []
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )

            default = win32print.GetDefaultPrinter()

            for printer in printer_list:
                printers.append({
                    'name': printer[2],
                    'is_default': printer[2] == default
                })

            logger.info(f"Найдено принтеров: {len(printers)}")
            return printers

        except Exception as e:
            logger.error(f"Ошибка получения принтеров: {e}")
            return []

    @staticmethod
    def get_default_printer() -> Optional[str]:
        """Получение принтера по умолчанию"""
        try:
            return win32print.GetDefaultPrinter()
        except Exception as e:
            logger.error(f"Ошибка получения принтера по умолчанию: {e}")
            return None

    @staticmethod
    def printer_exists(printer_name: str) -> bool:
        """Проверка существования принтера"""
        printers = PrinterService.get_printers()
        return any(p['name'] == printer_name for p in printers)

    @staticmethod
    def print_image(file_path: str, printer_name: Optional[str] = None) -> str:
        """
        Печать изображения на термопринтере.
        Масштабирует под ширину принтера, сохраняя пропорции.

        Args:
            file_path: Путь к PNG изображению
            printer_name: Имя принтера

        Returns:
            ID задания печати
        """
        hdc = None

        try:
            if not printer_name:
                printer_name = PrinterService.get_default_printer()

            if not printer_name:
                raise ValueError("Принтер не указан")

            if not PrinterService.printer_exists(printer_name):
                raise ValueError(f"Принтер не найден: {printer_name}")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Файл не найден: {file_path}")

            logger.info(f"Печать: {file_path} -> {printer_name}")

            # === ОТКРЫВАЕМ ИЗОБРАЖЕНИЕ ===
            image = Image.open(file_path)
            original_mode = image.mode
            original_size = image.size

            logger.info(f"Исходное: {original_size}, режим: {original_mode}")

            # === КОНВЕРТАЦИЯ В RGB ===
            if image.mode == 'RGBA':
                background = Image.new('RGBA', image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, image)
                image = image.convert('RGB')
            elif image.mode in ('LA', 'P'):
                image = image.convert('RGBA')
                background = Image.new('RGBA', image.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, image)
                image = image.convert('RGB')
            elif image.mode == 'L':
                image = image.convert('RGB')
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            # === СОЗДАЁМ КОНТЕКСТ ПРИНТЕРА ===
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer_name)

            printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
            printable_height = hdc.GetDeviceCaps(win32con.VERTRES)

            image_width, image_height = image.size

            logger.info(f"Принтер: {printable_width}x{printable_height}")

            # === МАСШТАБИРОВАНИЕ ПОД ШИРИНУ ПРИНТЕРА ===
            if image_width != printable_width:
                scale = printable_width / image_width
                new_width = printable_width
                new_height = int(image_height * scale)
                image = image.resize((new_width, new_height), Image.LANCZOS)
                logger.info(
                    f"Масштабировано: {image_width}x{image_height} -> "
                    f"{new_width}x{new_height} (scale={scale:.4f})"
                )
            else:
                new_width, new_height = image_width, image_height
                logger.info(f"Масштабирование не требуется: {new_width}x{new_height}")

            # === ПРОВЕРКА ИЗОБРАЖЕНИЯ ===
            extrema = image.getextrema()
            logger.info(f"RGB после обработки: {extrema}")
            if extrema == ((255, 255), (255, 255), (255, 255)):
                logger.error("ОШИБКА: Изображение полностью белое!")
            elif extrema == ((0, 0), (0, 0), (0, 0)):
                logger.error("ОШИБКА: Изображение полностью чёрное!")

            # === СОХРАНЯЕМ ДЛЯ ОТЛАДКИ ===
            debug_path = file_path + "_FINAL.png"
            image.save(debug_path, 'PNG')
            logger.info(f"DEBUG сохранено: {debug_path}")

            # === ПЕЧАТЬ ===
            x, y = 0, 0
            logger.info(f"Печать: pos=({x},{y}), size={new_width}x{new_height}")

            hdc.StartDoc(os.path.basename(file_path))
            hdc.StartPage()

            dib = ImageWin.Dib(image)
            dib.draw(hdc.GetHandleOutput(), (x, y, x + new_width, y + new_height))

            hdc.EndPage()
            hdc.EndDoc()

            job_id = str(uuid.uuid4())
            logger.info(f"Напечатано. Job ID: {job_id}")

            return job_id

        except Exception as e:
            logger.error(f"Ошибка печати: {e}")
            raise

        finally:
            if hdc:
                try:
                    hdc.DeleteDC()
                except Exception:
                    pass
