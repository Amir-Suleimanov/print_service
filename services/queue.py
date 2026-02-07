"""
Модуль управления очередью печати
"""
import threading
import time
import uuid
from dataclasses import dataclass
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
    image_data: bytes
    printer_name: str
    copies: int
    status: JobStatus
    created_at: str
    updated_at: str
    error_message: Optional[str] = None


class PrintQueue:
    """Очередь заданий печати"""

    def __init__(self, max_retries: int = 3):
        self.jobs: Dict[str, PrintJob] = {}
        self.max_retries = max_retries
        self.lock = threading.Lock()
        self.processing_thread = None
        self.is_running = False

    def add_job(self, image_data: bytes, printer_name: str, copies: int = 1) -> str:
        """Добавление задания в очередь"""
        job_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        job = PrintJob(
            job_id=job_id,
            image_data=image_data,
            printer_name=printer_name,
            copies=copies,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

        with self.lock:
            self.jobs[job_id] = job
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

    def get_pending_jobs(self) -> List[PrintJob]:
        with self.lock:
            return [job for job in self.jobs.values() if job.status == JobStatus.PENDING]

    def start_processing(self, printer_service):
        if self.is_running:
            return

        self.is_running = True
        self.processing_thread = threading.Thread(
            target=self._process_queue,
            args=(printer_service,),
            daemon=True,
        )
        self.processing_thread.start()

    def stop_processing(self):
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)

    def _process_queue(self, printer_service):
        while self.is_running:
            try:
                pending_jobs = self.get_pending_jobs()

                for job in pending_jobs:
                    if not self.is_running:
                        break

                    try:
                        self.update_job_status(job.job_id, JobStatus.PROCESSING)

                        for _ in range(job.copies):
                            printer_service.print_image(job.image_data, job.printer_name)

                        self.update_job_status(job.job_id, JobStatus.COMPLETED)

                    except Exception as e:
                        logger.error(f"Ошибка выполнения задания {job.job_id}: {e}")
                        self.update_job_status(job.job_id, JobStatus.FAILED, str(e))

                time.sleep(2)

            except Exception as e:
                logger.error(f"Ошибка в потоке обработки очереди: {e}")
                time.sleep(5)


_queue_instance: Optional[PrintQueue] = None


def get_print_queue() -> PrintQueue:
    """Получение глобального экземпляра очереди"""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = PrintQueue()
    return _queue_instance
