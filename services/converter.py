"""
Модуль конвертации файлов для печати
"""
import base64
from io import BytesIO
from PIL import Image
import magic

from utils.logger import get_logger

logger = get_logger()


class FileConverter:
    """Класс для конвертации файлов"""

    def __init__(self):
        self.magic = magic.Magic(mime=True)

    def decode_base64(self, data: str) -> bytes:
        """
        Декодирование base64 строки в файл

        Args:
            data: Base64 строка (с префиксом data:... или без)

        Returns:
            Декодированные данные файла
        """
        try:
            if ',' in data and data.startswith('data:'):
                data = data.split(',', 1)[1]

            file_data = base64.b64decode(data)

            if len(file_data) == 0:
                raise ValueError("Декодированные данные пустые")

            mime_type = self.magic.from_buffer(file_data)

            if not mime_type.startswith("image/"):
                raise ValueError(f"Неподдерживаемый MIME тип: {mime_type}")

            with Image.open(BytesIO(file_data)) as test_image:
                test_image.verify()

            return file_data

        except Exception as e:
            logger.error(f"Ошибка декодирования base64: {e}")
            raise ValueError(f"Не удалось декодировать base64: {e}")

    def normalize_to_png(self, file_data: bytes) -> bytes:
        """
        Нормализация изображения в PNG.
        Сохраняет прозрачность.
        """
        try:
            with Image.open(BytesIO(file_data)) as image:
                if image.mode == 'P':
                    if 'transparency' in image.info:
                        image = image.convert('RGBA')
                    else:
                        image = image.convert('RGB')

                output = BytesIO()
                image.save(output, 'PNG')
                return output.getvalue()

        except Exception as e:
            logger.error(f"Ошибка нормализации: {e}")
            raise ValueError(f"Не удалось нормализовать: {e}")
