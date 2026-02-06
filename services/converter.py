"""
Модуль конвертации файлов для печати
"""
import base64
import tempfile
import os
from pathlib import Path
from PIL import Image
import magic

from utils.logger import get_logger

logger = get_logger()


class FileConverter:
    """Класс для конвертации файлов"""

    def __init__(self, temp_folder: str = "./temp"):
        self.temp_folder = Path(temp_folder)
        self.temp_folder.mkdir(parents=True, exist_ok=True)
        self.magic = magic.Magic(mime=True)

    def decode_base64(self, data: str) -> str:
        """
        Декодирование base64 строки в файл

        Args:
            data: Base64 строка (с префиксом data:... или без)

        Returns:
            Путь к временному файлу
        """
        try:
            if ',' in data and data.startswith('data:'):
                data = data.split(',', 1)[1]

            file_data = base64.b64decode(data)

            if len(file_data) == 0:
                raise ValueError("Декодированные данные пустые")

            mime_type = self.magic.from_buffer(file_data)
            logger.debug(f"MIME тип: {mime_type}, размер: {len(file_data)} байт")

            extension = self._get_extension_from_mime(mime_type)

            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension,
                dir=self.temp_folder
            )
            temp_file.write(file_data)
            temp_file.close()

            try:
                test_image = Image.open(temp_file.name)
                logger.info(f"Декодировано: размер={test_image.size}, режим={test_image.mode}")
                logger.info(f"Диапазон цветов: {test_image.getextrema()}")
            except Exception as e:
                logger.warning(f"Не удалось открыть декодированное изображение: {e}")

            logger.info(f"Base64 декодирован: {temp_file.name}")
            return temp_file.name

        except Exception as e:
            logger.error(f"Ошибка декодирования base64: {e}")
            raise ValueError(f"Не удалось декодировать base64: {e}")

    def _get_extension_from_mime(self, mime_type: str) -> str:
        """Получение расширения из MIME типа"""
        mime_map = {
            'image/png': '.png',
            'image/jpeg': '.jpg',
            'image/jpg': '.jpg',
            'image/bmp': '.bmp',
            'image/gif': '.gif',
        }
        return mime_map.get(mime_type, '.png')

    def normalize_to_png(self, file_path: str) -> str:
        """
        Нормализация изображения в PNG БЕЗ заливки фона.
        Сохраняет прозрачность для термопринтера.

        Args:
            file_path: Путь к исходному изображению

        Returns:
            Путь к нормализованному PNG
        """
        try:
            image = Image.open(file_path)
            original_mode = image.mode

            # Конвертируем только проблемные режимы, сохраняя прозрачность.
            if image.mode in ('P', 'LA', 'L'):
                image = image.convert('RGBA')

            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.png',
                dir=self.temp_folder
            )
            temp_file.close()

            image.save(temp_file.name, 'PNG')
            logger.info(f"PNG нормализован: {temp_file.name} ({original_mode} -> {image.mode})")

            return temp_file.name

        except Exception as e:
            logger.error(f"Ошибка нормализации: {e}")
            raise ValueError(f"Не удалось нормализовать изображение: {e}")

    def cleanup(self, file_path: str):
        """Удаление временного файла"""
        try:
            if os.path.exists(file_path) and str(self.temp_folder) in file_path:
                os.remove(file_path)
                logger.debug(f"Удалён: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить {file_path}: {e}")
