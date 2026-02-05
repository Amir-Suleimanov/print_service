"""
Модуль валидации API запросов
"""
from typing import Optional, Dict
from pydantic import BaseModel, Field, validator
from enum import Enum


class DataType(str, Enum):
    """Типы данных для печати"""
    FILE = "file"
    BASE64 = "base64"
    URL = "url"


class FileFormat(str, Enum):
    """Форматы файлов"""
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"
    RAW = "raw"
    AUTO = "auto"


class Orientation(str, Enum):
    """Ориентация страницы"""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PaperSize(str, Enum):
    """Размеры бумаги"""
    A4 = "A4"
    A5 = "A5"
    LETTER = "Letter"


class PrintOptions(BaseModel):
    """Опции печати"""
    orientation: Optional[Orientation] = Field(default=Orientation.PORTRAIT, description="Ориентация страницы")
    paper_size: Optional[PaperSize] = Field(default=PaperSize.A4, description="Размер бумаги")
    duplex: Optional[bool] = Field(default=False, description="Двусторонняя печать")
    color: Optional[bool] = Field(default=True, description="Цветная печать")
    
    class Config:
        use_enum_values = True


class PrintRequest(BaseModel):
    """Запрос на печать"""
    type: DataType = Field(..., description="Тип данных (file, base64, url)")
    data: str = Field(..., description="Данные для печати (путь к файлу, base64 строка или URL)")
    format: FileFormat = Field(default=FileFormat.AUTO, description="Формат файла")
    printer: Optional[str] = Field(default=None, description="Имя принтера (опционально)")
    copies: Optional[int] = Field(default=1, ge=1, le=100, description="Количество копий (1-100)")
    options: Optional[PrintOptions] = Field(default=None, description="Опции печати")
    
    @validator('data')
    def validate_data(cls, v, values):
        """Валидация данных"""
        if not v or not v.strip():
            raise ValueError("Данные не могут быть пустыми")
        
        # Проверка размера base64 строки (примерно)
        if values.get('type') == DataType.BASE64:
            # Грубая оценка: base64 примерно на 33% больше исходного размера
            # Ограничим 100 МБ в base64 (примерно 75 МБ исходный файл)
            if len(v) > 100 * 1024 * 1024:
                raise ValueError("Base64 строка слишком большая (максимум ~75 МБ)")
        
        return v
    
    class Config:
        use_enum_values = True


class PrintResponse(BaseModel):
    """Ответ на запрос печати"""
    success: bool = Field(..., description="Успешность операции")
    job_id: Optional[str] = Field(default=None, description="ID задания печати")
    message: str = Field(..., description="Сообщение")


class JobStatusResponse(BaseModel):
    """Ответ со статусом задания"""
    success: bool
    job_id: str
    status: str
    created_at: str
    updated_at: str
    error_message: Optional[str] = None


class PrinterInfo(BaseModel):
    """Информация о принтере"""
    name: str
    status: str
    is_default: bool


class PrintersResponse(BaseModel):
    """Ответ со списком принтеров"""
    success: bool
    printers: list[PrinterInfo]
    count: int


class HealthResponse(BaseModel):
    """Ответ healthcheck"""
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    success: bool = False
    error: str
    details: Optional[str] = None
