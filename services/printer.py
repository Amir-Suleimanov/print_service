"""
Модуль работы с принтерами Windows
"""
import os
import uuid
from io import BytesIO
import win32print
from PIL import Image
from typing import List, Dict, Optional, Union

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
    def print_image(file_input: Union[str, bytes], printer_name: Optional[str] = None) -> str:
        """
        Печать изображения на термопринтере TG2480 через ESC/POS.
        С центрированием и автоматической обрезкой.
        """
        try:
            if not printer_name:
                printer_name = PrinterService.get_default_printer()

            if not printer_name:
                raise ValueError("Принтер не указан")

            if not PrinterService.printer_exists(printer_name):
                raise ValueError(f"Принтер не найден: {printer_name}")

            # === ОТКРЫВАЕМ ИЗОБРАЖЕНИЕ ===
            if isinstance(file_input, bytes):
                image = Image.open(BytesIO(file_input))
            else:
                if not os.path.exists(file_input):
                    raise FileNotFoundError(f"Файл не найден: {file_input}")
                image = Image.open(file_input)

            # === ОБРАБОТКА ПРОЗРАЧНОСТИ → GRAYSCALE ===
            if image.mode == 'RGBA':
                r, g, b, a = image.split()
                rgb_image = Image.merge('RGB', (r, g, b))
                gray = rgb_image.convert('L')
                result = Image.new('L', image.size, 255)
                result.paste(gray, mask=a)
                image = result
            elif image.mode == 'LA':
                l, a = image.split()
                result = Image.new('L', image.size, 255)
                result.paste(l, mask=a)
                image = result
            elif image.mode == 'P':
                if 'transparency' in image.info:
                    image = image.convert('RGBA')
                    r, g, b, a = image.split()
                    rgb_image = Image.merge('RGB', (r, g, b))
                    gray = rgb_image.convert('L')
                    result = Image.new('L', image.size, 255)
                    result.paste(gray, mask=a)
                    image = result
                else:
                    image = image.convert('L')
            elif image.mode != 'L':
                image = image.convert('L')

            # === ПАРАМЕТРЫ ПРИНТЕРА ===
            PRINTABLE_WIDTH = 608  # Ширина области печати TG2480 (80mm бумага)
            MAX_WIDTH = 512        # Максимальная ширина изображения
            
            # === МАСШТАБИРОВАНИЕ ===
            image_width, image_height = image.size
            if image_width > MAX_WIDTH:
                scale = MAX_WIDTH / image_width
                new_width = MAX_WIDTH
                new_height = int(image_height * scale)
                image = image.resize((new_width, new_height), Image.LANCZOS)

            # === КОНВЕРТАЦИЯ В 1-BIT ===
            image = image.point(lambda x: 0 if x < 128 else 255, '1')
            
            width, height = image.size

            # === РАСЧЁТ ЦЕНТРИРОВАНИЯ ===
            left_margin = (PRINTABLE_WIDTH - width) // 2
            margin_nL = left_margin % 256
            margin_nH = left_margin // 256

            # === ФОРМИРОВАНИЕ ESC/POS ДАННЫХ ===
            esc_pos_data = bytearray()
            
            # 1. Инициализация принтера
            esc_pos_data += b'\x1B\x40'  # ESC @ - Initialize
            
            # 2. Установка левого поля для центрирования
            # GS L nL nH
            esc_pos_data += b'\x1D\x4C'  # GS L
            esc_pos_data += bytes([margin_nL, margin_nH])
            
            # 3. Межстрочный интервал = 0 для графики
            esc_pos_data += b'\x1B\x33\x00'  # ESC 3 0
            
            # 4. Данные изображения
            nL = width % 256
            nH = width // 256
            
            pixels = image.load()
            
            for y_block in range(0, height, 24):
                # ESC * 33 nL nH (24-dot double density)
                esc_pos_data += b'\x1B\x2A\x21'
                esc_pos_data += bytes([nL, nH])
                
                for x in range(width):
                    for byte_num in range(3):
                        byte_val = 0
                        for bit in range(8):
                            y = y_block + byte_num * 8 + bit
                            if y < height:
                                pixel = pixels[x, y]
                                if pixel == 0:  # Чёрный = печатать
                                    byte_val |= (0x80 >> bit)
                        esc_pos_data += bytes([byte_val])
                
                # Перевод строки
                esc_pos_data += b'\x0A'
            
            # 5. Восстановление межстрочного интервала
            esc_pos_data += b'\x1B\x32'  # ESC 2
            
            # 6. TG2480: полная обрезка + автоматический обратный прогон бумаги.
            # Команда убирает лишний верхний отступ перед следующей печатью.
            # HEX: 1C C0 AA 0F EE 0B 34
            esc_pos_data += b'\x1C\xC0\xAA\x0F\xEE\x0B\x34'

            # === ОТПРАВКА НА ПРИНТЕР ===
            hprinter = win32print.OpenPrinter(printer_name)
            try:
                job_info = ("ESC/POS Image", None, "RAW")
                win32print.StartDocPrinter(hprinter, 1, job_info)
                try:
                    win32print.StartPagePrinter(hprinter)
                    win32print.WritePrinter(hprinter, bytes(esc_pos_data))
                    win32print.EndPagePrinter(hprinter)
                finally:
                    win32print.EndDocPrinter(hprinter)
            finally:
                win32print.ClosePrinter(hprinter)

            result_id = str(uuid.uuid4())

            return result_id

        except Exception as e:
            logger.error(f"Ошибка печати: {e}")
            raise
