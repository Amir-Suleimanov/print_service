"""
Модуль управления очередью печати
"""
import json
import threading
import time
import uuid
from dataclasses import dataclass
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


@dataclass
class PrintJob:
    """Задание на печать"""
    job_id: str
    file_path: str
    printer_name: str
    copies: int
    status: JobStatus
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'job_id': self.job_id,
            'file_path': self.file_path,
            'printer_name': self.printer_name,
            'copies': self.copies,
            'status': self.status.value,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'error_message': self.error_message,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'PrintJob':
        status_raw = data.get('status', JobStatus.PENDING.value)
        try:
            status = JobStatus(status_raw)
        except ValueError:
            status = JobStatus.PENDING

        return PrintJob(
            job_id=data['job_id'],
            file_path=data['file_path'],
            printer_name=data['printer_name'],
            copies=data.get('copies', 1),
            status=status,
            created_at=data['created_at'],
            updated_at=data.get('updated_at', data['created_at']),
            error_message=data.get('error_message'),
        )


class PrintQueue:
    """Очередь заданий печати"""

    def __init__(self, persistence_file: str = "./temp/queue.json", max_retries: int = 3):
        self.jobs: Dict[str, PrintJob] = {}
        self.persistence_file = Path(persistence_file)
        self.max_retries = max_retries
        self.lock = threading.Lock()
        self.processing_thread = None
        self.is_running = False

        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        self._load_queue()

    def add_job(self, file_path: str, printer_name: str, copies: int = 1) -> str:
        """Добавление задания в очередь"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        job = PrintJob(
            job_id=job_id,
            file_path=file_path,
            printer_name=printer_name,
            copies=copies,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        with self.lock:
            self.jobs[job_id] = job
            self._save_queue()

        logger.info(f"Задание добавлено: {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[PrintJob]:
        with self.lock:
            return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[PrintJob]:
        with self.lock:
            return list(self.jobs.values())

    def update_job_status(self, job_id: str, status: JobStatus, error_message: Optional[str] = None):
        with self.lock:
            job = self.jobs.get(job_id)
            if job:
                job.status = status
                job.updated_at = datetime.now().isoformat()
                if error_message:
                    job.error_message = error_message
                self._save_queue()
                logger.debug(f"Статус задания {job_id} обновлён: {status.value}")

    def get_pending_jobs(self) -> List[PrintJob]:
        with self.lock:
            return [job for job in self.jobs.values() if job.status == JobStatus.PENDING]

    def start_processing(self, printer_service):
        if self.is_running:
            logger.warning("Обработка очереди уже запущена")
            return

        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_queue,
            args=(printer_service,),
            daemon=True,
        )
        self.processing_thread.start()
        logger.info("Обработка очереди запущена")

    def stop_processing(self):
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        logger.info("Обработка очереди остановлена")

    def _process_queue(self, printer_service):
        logger.info("Поток обработки очереди запущен")

        while self.is_running:
            try:
                pending_jobs = self.get_pending_jobs()

                for job in pending_jobs:
                    if not self.is_running:
                        break

                    try:
                        self.update_job_status(job.job_id, JobStatus.PROCESSING)
                        logger.info(f"Обработка задания: {job.job_id}")

                        for _ in range(job.copies):
                            printer_service.print_image(job.file_path, job.printer_name)

                        self.update_job_status(job.job_id, JobStatus.COMPLETED)
                        logger.info(f"Задание выполнено: {job.job_id}")

                    except Exception as e:
                        logger.error(f"Ошибка выполнения задания {job.job_id}: {e}")
                        self.update_job_status(job.job_id, JobStatus.FAILED, str(e))

                time.sleep(2)

            except Exception as e:
                logger.error(f"Ошибка в потоке обработки очереди: {e}")
                time.sleep(5)

        logger.info("Поток обработки очереди завершён")

    def _save_queue(self):
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
        try:
            if self.persistence_file.exists():
                with open(self.persistence_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for job_data in data.get('jobs', []):
                    # Совместимость со старым форматом очереди.
                    if 'printer_name' not in job_data and 'printer' in job_data:
                        job_data['printer_name'] = job_data['printer']
                    if 'copies' not in job_data:
                        job_data['copies'] = 1

                    job = PrintJob.from_dict(job_data)
                    if job.status == JobStatus.PROCESSING:
                        job.status = JobStatus.PENDING
                    self.jobs[job.job_id] = job

                logger.info(f"Загружено заданий из очереди: {len(self.jobs)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки очереди: {e}")


_queue_instance: Optional[PrintQueue] = None


def get_print_queue() -> PrintQueue:
    """Получение глобального экземпляра очереди"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = PrintQueue()
    return _queue_instance
