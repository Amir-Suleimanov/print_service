"""
Валидаторы запросов API
"""
from pydantic import BaseModel, Field, AliasChoices
from typing import Optional


class PrintRequest(BaseModel):
    """Запрос на печать base64 изображения"""
    image: str = Field(
        ...,
        description="Base64 строка изображения",
        validation_alias=AliasChoices("image", "jpeg"),
    )
    printer: Optional[str] = Field(None, description="Имя принтера")
    copies: int = Field(1, ge=1, le=100, description="Количество копий")


class PrintResponse(BaseModel):
    """Ответ на запрос печати"""
    success: bool
    job_id: str
    message: str


class HealthResponse(BaseModel):
    """Ответ healthcheck"""
    status: str
    service: str
    version: str


class ErrorResponse(BaseModel):
    """Ответ с ошибкой"""
    error: str
    details: str
