"""
REST API для сервиса печати
"""
import json
from flask import Flask, request, jsonify
from functools import wraps
from typing import Dict

from api.validators import PrintRequest, PrintResponse, ErrorResponse
from services.printer import PrinterService
from services.converter import FileConverter
from services.queue import get_print_queue
from utils.logger import get_logger

logger = get_logger()
API_KEY = ""
DEFAULT_PRINTER = ""


def create_app():
    """Создание Flask приложения"""
    app = Flask(__name__)

    converter = FileConverter()
    printer_service = PrinterService()
    print_queue = get_print_queue()

    print_queue.start_processing(printer_service)

    def require_api_key(f):
        """Декоратор проверки API ключа"""
        @wraps(f)
        def decorated(*args, **kwargs):
            if API_KEY:
                api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
                if not api_key or api_key != API_KEY:
                    return jsonify(ErrorResponse(
                        error="Unauthorized",
                        details="Требуется API ключ",
                    ).dict()), 401
            return f(*args, **kwargs)
        return decorated

    def parse_json() -> Dict:
        """Парсинг JSON из запроса"""
        data = request.get_json(silent=True)
        if data is not None:
            return data

        raw = request.get_data(as_text=True)
        if not raw:
            return {}

        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("JSON должен быть объектом")
        return parsed

    @app.route('/health', methods=['GET'])
    def health():
        """Проверка работоспособности сервиса"""
        return jsonify({
            "status": "ok",
            "service": "PrintService",
            "host": "127.0.0.1",
            "port": 8101
        })
    
    @app.route('/Print', methods=['POST'])
    @require_api_key
    def print_image():
        """
        Печать base64 изображения

        Body:
        {
            "image": "base64 строка",
            "printer": "имя принтера (опционально)",
            "copies": 1
        }
        """
        try:
            try:
                data = parse_json()
                req = PrintRequest(**data)
            except Exception as e:
                return jsonify(ErrorResponse(
                    error="Некорректный запрос",
                    details=str(e),
                ).dict()), 400

            try:
                decoded_data = converter.decode_base64(req.image)
                normalized_data = converter.normalize_to_png(decoded_data)
            except Exception as e:
                logger.error(f"Ошибка подготовки: {e}")
                return jsonify(ErrorResponse(
                    error="Ошибка подготовки файла",
                    details=str(e),
                ).dict()), 400

            printer_name = req.printer
            if not printer_name:
                printer_name = DEFAULT_PRINTER or printer_service.get_default_printer()

            if not printer_name:
                return jsonify(ErrorResponse(
                    error="Принтер не указан",
                    details="Укажите принтер или настройте по умолчанию",
                ).dict()), 400

            if not printer_service.printer_exists(printer_name):
                return jsonify(ErrorResponse(
                    error="Принтер не найден",
                    details=f"Принтер '{printer_name}' не найден",
                ).dict()), 404

            job_id = print_queue.add_job(
                image_data=normalized_data,
                printer_name=printer_name,
                copies=req.copies,
            )

            return jsonify(PrintResponse(
                success=True,
                job_id=job_id,
                message="Отправлено в очередь печати",
            ).dict()), 200

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return jsonify(ErrorResponse(
                error="Внутренняя ошибка",
                details=str(e),
            ).dict()), 500

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(ErrorResponse(
            error="Не найдено",
            details="Эндпоинт не существует",
        ).dict()), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(ErrorResponse(
            error="Внутренняя ошибка",
            details=str(e),
        ).dict()), 500

    return app
