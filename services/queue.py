"""
Модуль управления очередью печати
"""
import json
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum

from utils.logger import get_logger

logger = get_logger()


class JobStatus(Enum):
    """Статусы задания печати"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrintJob:
    """Класс задания на печать"""
    
    def __init__(self, job_id: str, file_path: str, file_format: str, 
                 printer_name: str, options: Optional[Dict] = None, copies: int = 1):
        self.job_id = job_id
        self.file_path = file_path
        self.file_format = file_format
        self.printer_name = printer_name
        self.options = options or {}
        self.copies = copies
        self.status = JobStatus.PENDING
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.error_message = None
        self.retry_count = 0
        self.max_retries = 3
    
    def to_dict(self) -> Dict:
        """Преобразование задания в словарь"""
        return {
            'job_id': self.job_id,
            'file_path': self.file_path,
            'file_format': self.file_format,
            'printer_name': self.printer_name,
            'options': self.options,
            'copies': self.copies,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'PrintJob':
        """Создание задания из словаря"""
        job = PrintJob(
            job_id=data['job_id'],
            file_path=data['file_path'],
            file_format=data['file_format'],
            printer_name=data['printer_name'],
            options=data.get('options', {}),
            copies=data.get('copies', 1)
        )
        job.status = JobStatus(data['status'])
        job.created_at = data['created_at']
        job.updated_at = data.get('updated_at', data['created_at'])
        job.error_message = data.get('error_message')
        job.retry_count = data.get('retry_count', 0)
        return job


class PrintQueue:
    """Очередь заданий печати"""
    
    def __init__(self, persistence_file: str = "./temp/queue.json", max_retries: int = 3):
        """
        Инициализация очереди
        
        Args:
            persistence_file: Файл для сохранения очереди
            max_retries: Максимальное количество повторных попыток
        """
        self.jobs: Dict[str, PrintJob] = {}
        self.persistence_file = Path(persistence_file)
        self.max_retries = max_retries
        self.lock = threading.Lock()
        self.processing_thread = None
        self.is_running = False
        
        # Создаём директорию если не существует
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Загружаем сохранённые задания
        self._load_queue()
    
    def add_job(self, file_path: str, file_format: str, printer_name: str, 
                options: Optional[Dict] = None, copies: int = 1) -> str:
        """
        Добавление задания в очередь
        
        Args:
            file_path: Путь к файлу
            file_format: Формат файла
            printer_name: Имя принтера
            options: Опции печати
            copies: Количество копий
            
        Returns:
            ID задания
        """
        job_id = str(uuid.uuid4())
        job = PrintJob(job_id, file_path, file_format, printer_name, options, copies)
        job.max_retries = self.max_retries
        
        with self.lock:
            self.jobs[job_id] = job
            self._save_queue()
        
        logger.info(f"Задание добавлено в очередь: {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[PrintJob]:
        """
        Получение задания по ID
        
        Args:
            job_id: ID задания
            
        Returns:
            Задание или None
        """
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[PrintJob]:
        """Получение всех заданий"""
        with self.lock:
            return list(self.jobs.values())
    
    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None):
        """
        Обновление статуса задания
        
        Args:
            job_id: ID задания
            status: Новый статус
            error_message: Сообщение об ошибке (опционально)
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = status
                job.updated_at = datetime.now().isoformat()
                if error_message:
                    job.error_message = error_message
                self._save_queue()
                logger.debug(f"Статус задания {job_id} обновлён: {status.value}")
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Отмена задания
        
        Args:
            job_id: ID задания
            
        Returns:
            True если успешно отменено
        """
        with self.lock:
            job = self.jobs.get(job_id)
            if job and job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
                job.status = JobStatus.CANCELLED
                job.updated_at = datetime.now().isoformat()
                self._save_queue()
                logger.info(f"Задание отменено: {job_id}")
                return True
        return False
    
    def get_pending_jobs(self) -> List[PrintJob]:
        """Получение заданий в ожидании"""
        with self.lock:
            return [job for job in self.jobs.values() if job.status == JobStatus.PENDING]
    
    def start_processing(self, printer_service):
        """
        Запуск обработки очереди в отдельном потоке
        
        Args:
            printer_service: Экземпляр PrinterService
        """
        if self.is_running:
            logger.warning("Обработка очереди уже запущена")
            return
        
        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_queue,
            args=(printer_service,),
            daemon=True
        )
        self.processing_thread.start()
        logger.info("Обработка очереди запущена")
    
    def stop_processing(self):
        """Остановка обработки очереди"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("Обработка очереди остановлена")
    
    def _process_queue(self, printer_service):
        """
        Обработка очереди заданий
        
        Args:
            printer_service: Экземпляр PrinterService
        """
        logger.info("Поток обработки очереди запущен")
        
        while self.is_running:
            try:
                # Получаем задания в ожидании
                pending_jobs = self.get_pending_jobs()
                
                for job in pending_jobs:
                    if not self.is_running:
                        break
                    
                    try:
                        # Обновляем статус
                        self.update_job_status(job.job_id, JobStatus.PROCESSING)
                        
                        # Печатаем файл
                        logger.info(f"Обработка задания: {job.job_id}")
                        printer_service.print_file(
                            job.file_path,
                            job.file_format,
                            job.printer_name,
                            job.options,
                            job.copies
                        )
                        
                        # Успешно выполнено
                        self.update_job_status(job.job_id, JobStatus.COMPLETED)
                        logger.info(f"Задание выполнено: {job.job_id}")
                        
                    except Exception as e:
                        logger.error(f"Ошибка выполнения задания {job.job_id}: {e}")
                        
                        # Проверяем возможность повтора
                        job.retry_count += 1
                        if job.retry_count < job.max_retries:
                            # Возвращаем в очередь
                            self.update_job_status(
                                job.job_id,
                                JobStatus.PENDING,
                                f"Попытка {job.retry_count}/{job.max_retries}: {str(e)}"
                            )
                            logger.info(f"Задание {job.job_id} будет повторено ({job.retry_count}/{job.max_retries})")
                        else:
                            # Превышено количество попыток
                            self.update_job_status(
                                job.job_id,
                                JobStatus.FAILED,
                                f"Превышено максимальное количество попыток: {str(e)}"
                            )
                
                # Ждём перед следующей итерацией
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Ошибка в потоке обработки очереди: {e}")
                time.sleep(5)
        
        logger.info("Поток обработки очереди завершён")
    
    def _save_queue(self):
        """Сохранение очереди в файл"""
        try:
            data = {
                'jobs': [job.to_dict() for job in self.jobs.values()]
            }
            with open(self.persistence_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Очередь сохранена")
        except Exception as e:
            logger.error(f"Ошибка сохранения очереди: {e}")
    
    def _load_queue(self):
        """Загрузка очереди из файла"""
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for job_data in data.get('jobs', []):
                    job = PrintJob.from_dict(job_data)
                    # Сбрасываем статус обрабатывающихся заданий
                    if job.status == JobStatus.PROCESSING:
                        job.status = JobStatus.PENDING
                    self.jobs[job.job_id] = job
                
                logger.info(f"Загружено заданий из очереди: {len(self.jobs)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки очереди: {e}")


# Глобальный экземпляр очереди
_queue_instance: Optional[PrintQueue] = None


def get_print_queue() -> PrintQueue:
    """Получение глобального экземпляра очереди"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = PrintQueue()
    return _queue_instance
