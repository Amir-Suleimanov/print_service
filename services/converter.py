"""
Модуль конвертации файлов для печати
"""
import base64
import os
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import magic

from utils.logger import get_logger

logger = get_logger()


class FileConverter:
    """Класс для конвертации файлов различных форматов"""
    
    def __init__(self, temp_folder: str = "./temp"):
        """
        Инициализация конвертера
        
        Args:
            temp_folder: Папка для временных файлов
        """
        self.temp_folder = Path(temp_folder)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        self.magic = magic.Magic(mime=True)
    
    def decode_base64(self, data: str, file_format: str = "auto") -> str:
        """
        Декодирование base64 строки в файл
        
        Args:
            data: Base64 строка
            file_format: Формат файла (pdf, image, auto)
            
        Returns:
            Путь к временному файлу
        """
        try:
            # Убираем возможный префикс data:image/png;base64,
            if ',' in data and data.startswith('data:'):
                data = data.split(',', 1)[1]
            
            # Декодируем base64
            file_data = base64.b64decode(data)
            
            # Определяем MIME тип
            mime_type = self.magic.from_buffer(file_data)
            logger.debug(f"Определён MIME тип: {mime_type}")
            
            # Определяем расширение файла
            extension = self._get_extension_from_mime(mime_type)
            
            # Создаём временный файл
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension,
                dir=self.temp_folder
            )
            
            temp_file.write(file_data)
            temp_file.close()
            
            logger.info(f"Base64 декодирован в файл: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Ошибка декодирования base64: {e}")
            raise ValueError(f"Не удалось декодировать base64: {e}")
    
    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Получение расширения файла из MIME типа"""
        mime_map = {
            'application/pdf': '.pdf',
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/bmp': '.bmp',
            'image/gif': '.gif',
            'image/tiff': '.tiff',
            'text/plain': '.txt'
        }
        return mime_map.get(mime_type, '.bin')
    
    def convert_image_to_pdf(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        Конвертация изображения в PDF для лучшей совместимости с принтерами
        
        Args:
            image_path: Путь к изображению
            output_path: Путь для сохранения PDF (опционально)
            
        Returns:
            Путь к PDF файлу
        """
        try:
            # Открываем изображение
            image = Image.open(image_path)
            
            # Конвертируем в RGB если необходимо (для RGBA, P и т.д.)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Создаём белый фон
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            elif image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Определяем путь для сохранения
            if output_path is None:
                output_path = str(self.temp_folder / f"{Path(image_path).stem}.pdf")
            
            # Сохраняем как PDF
            image.save(output_path, 'PDF', resolution=100.0)
            logger.info(f"Изображение конвертировано в PDF: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка конвертации изображения в PDF: {e}")
            raise ValueError(f"Не удалось конвертировать изображение: {e}")
    
    def prepare_file(self, data: str, data_type: str, file_format: str = "auto") -> Tuple[str, str]:
        """
        Подготовка файла для печати
        
        Args:
            data: Данные (путь к файлу, base64 строка или URL)
            data_type: Тип данных (file, base64, url)
            file_format: Формат файла (pdf, image, auto)
            
        Returns:
            Кортеж (путь к файлу, формат файла)
        """
        try:
            if data_type == "base64":
                # Декодируем base64
                file_path = self.decode_base64(data, file_format)
                
            elif data_type == "file":
                # Проверяем существование файла
                if not os.path.exists(data):
                    raise FileNotFoundError(f"Файл не найден: {data}")
                file_path = data
                
            elif data_type == "url":
                # TODO: Реализовать загрузку по URL
                raise NotImplementedError("Загрузка по URL пока не реализована")
            
            else:
                raise ValueError(f"Неизвестный тип данных: {data_type}")
            
            # Определяем формат файла
            detected_format = self._detect_file_format(file_path)
            
            logger.info(f"Файл подготовлен: {file_path}, формат: {detected_format}")
            return file_path, detected_format
            
        except Exception as e:
            logger.error(f"Ошибка подготовки файла: {e}")
            raise
    
    def _detect_file_format(self, file_path: str) -> str:
        """
        Определение формата файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Формат файла (pdf, image, text, raw)
        """
        try:
            mime_type = self.magic.from_file(file_path)
            
            if mime_type == 'application/pdf':
                return 'pdf'
            elif mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('text/'):
                return 'text'
            else:
                return 'raw'
                
        except Exception as e:
            logger.warning(f"Не удалось определить MIME тип, проверяю расширение: {e}")
            
            # Fallback на расширение файла
            ext = Path(file_path).suffix.lower()
            if ext == '.pdf':
                return 'pdf'
            elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
                return 'image'
            elif ext == '.txt':
                return 'text'
            else:
                return 'raw'
    
    def cleanup_temp_file(self, file_path: str):
        """
        Удаление временного файла
        
        Args:
            file_path: Путь к файлу
        """
        try:
            if os.path.exists(file_path) and str(self.temp_folder) in file_path:
                os.remove(file_path)
                logger.debug(f"Временный файл удалён: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить временный файл {file_path}: {e}")
