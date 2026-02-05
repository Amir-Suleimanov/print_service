"""
REST API эндпоинты для сервиса печати
"""
from flask import Flask, request, jsonify
from functools import wraps
from typing import Dict

from api.validators import (
    PrintRequest, PrintResponse, JobStatusResponse,
    PrintersResponse, PrinterInfo, HealthResponse, ErrorResponse
)
from services.printer import PrinterService
from services.converter import FileConverter
from services.queue import get_print_queue, JobStatus
from config import get_config
from utils.logger import get_logger

logger = get_logger()


def create_app():
    """Создание Flask приложения"""
    app = Flask(__name__)
    config = get_config()
    
    # Инициализация сервисов
    converter = FileConverter(config.temp_folder)
    printer_service = PrinterService()
    print_queue = get_print_queue()
    
    # Запускаем обработку очереди
    print_queue.start_processing(printer_service)
    
    def require_api_key(f):
        """Декоратор для проверки API ключа"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if config.requires_api_key:
                api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
                if not api_key or api_key != config.api_key:
                    return jsonify(ErrorResponse(
                        error="Unauthorized",
                        details="Требуется валидный API ключ"
                    ).dict()), 401
            return f(*args, **kwargs)
        return decorated_function
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """Healthcheck эндпоинт"""
        return jsonify(HealthResponse(
            status="healthy",
            service="Print Service",
            version="1.0.0"
        ).dict())
    
    @app.route('/api/printers', methods=['GET'])
    @require_api_key
    def get_printers():
        """Получение списка принтеров"""
        try:
            printers = printer_service.get_printers()
            printer_list = [PrinterInfo(**p).dict() for p in printers]
            
            return jsonify(PrintersResponse(
                success=True,
                printers=printer_list,
                count=len(printer_list)
            ).dict())
            
        except Exception as e:
            logger.error(f"Ошибка получения списка принтеров: {e}")
            return jsonify(ErrorResponse(
                error="Ошибка получения принтеров",
                details=str(e)
            ).dict()), 500
    
    @app.route('/api/print', methods=['POST'])
    @require_api_key
    def print_file():
        """Печать файла"""
        try:
            # Валидация запроса
            try:
                data = request.get_json()
                print_req = PrintRequest(**data)
            except Exception as e:
                logger.warning(f"Ошибка валидации запроса: {e}")
                return jsonify(ErrorResponse(
                    error="Некорректный запрос",
                    details=str(e)
                ).dict()), 400
            
            # Подготовка файла
            try:
                file_path, file_format = converter.prepare_file(
                    print_req.data,
                    print_req.type,
                    print_req.format
                )
            except Exception as e:
                logger.error(f"Ошибка подготовки файла: {e}")
                return jsonify(ErrorResponse(
                    error="Ошибка подготовки файла",
                    details=str(e)
                ).dict()), 400
            
            # Определяем принтер
            printer_name = print_req.printer
            if not printer_name:
                printer_name = config.default_printer or printer_service.get_default_printer()
            
            if not printer_name:
                return jsonify(ErrorResponse(
                    error="Принтер не указан",
                    details="Укажите принтер в запросе или настройте принтер по умолчанию"
                ).dict()), 400
            
            # Проверяем существование принтера
            if not printer_service.printer_exists(printer_name):
                return jsonify(ErrorResponse(
                    error="Принтер не найден",
                    details=f"Принтер '{printer_name}' не найден в системе"
                ).dict()), 404
            
            # Добавляем задание в очередь
            job_id = print_queue.add_job(
                file_path=file_path,
                file_format=file_format,
                printer_name=printer_name,
                options=print_req.options.dict() if print_req.options else {},
                copies=print_req.copies
            )
            
            logger.info(f"Задание печати создано: {job_id}")
            
            return jsonify(PrintResponse(
                success=True,
                job_id=job_id,
                message="Задание отправлено в очередь печати"
            ).dict()), 200
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка при печати: {e}")
            return jsonify(ErrorResponse(
                error="Внутренняя ошибка сервера",
                details=str(e)
            ).dict()), 500
    
    @app.route('/api/status/<job_id>', methods=['GET'])
    @require_api_key
    def get_job_status(job_id: str):
        """Получение статуса задания"""
        try:
            job = print_queue.get_job(job_id)
            
            if not job:
                return jsonify(ErrorResponse(
                    error="Задание не найдено",
                    details=f"Задание с ID '{job_id}' не существует"
                ).dict()), 404
            
            return jsonify(JobStatusResponse(
                success=True,
                job_id=job.job_id,
                status=job.status.value,
                created_at=job.created_at,
                updated_at=job.updated_at,
                error_message=job.error_message
            ).dict())
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса задания: {e}")
            return jsonify(ErrorResponse(
                error="Ошибка получения статуса",
                details=str(e)
            ).dict()), 500
    
    @app.route('/api/cancel/<job_id>', methods=['DELETE'])
    @require_api_key
    def cancel_job(job_id: str):
        """Отмена задания печати"""
        try:
            success = print_queue.cancel_job(job_id)
            
            if not success:
                return jsonify(ErrorResponse(
                    error="Не удалось отменить задание",
                    details="Задание не найдено или уже выполнено"
                ).dict()), 400
            
            return jsonify(PrintResponse(
                success=True,
                job_id=job_id,
                message="Задание отменено"
            ).dict())
            
        except Exception as e:
            logger.error(f"Ошибка отмены задания: {e}")
            return jsonify(ErrorResponse(
                error="Ошибка отмены задания",
                details=str(e)
            ).dict()), 500
    
    @app.route('/api/queue', methods=['GET'])
    @require_api_key
    def get_queue():
        """Получение всех заданий в очереди"""
        try:
            jobs = print_queue.get_all_jobs()
            jobs_data = [job.to_dict() for job in jobs]
            
            return jsonify({
                'success': True,
                'jobs': jobs_data,
                'count': len(jobs_data)
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения очереди: {e}")
            return jsonify(ErrorResponse(
                error="Ошибка получения очереди",
                details=str(e)
            ).dict()), 500
    
    # Обработчик ошибок 404
    @app.errorhandler(404)
    def not_found(e):
        return jsonify(ErrorResponse(
            error="Не найдено",
            details="Эндпоинт не существует"
        ).dict()), 404
    
    # Обработчик ошибок 500
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify(ErrorResponse(
            error="Внутренняя ошибка сервера",
            details=str(e)
        ).dict()), 500
    
    return app
