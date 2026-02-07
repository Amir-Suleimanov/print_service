"""
Модуль управления конфигурацией сервиса печати
"""
import json
import os
from pathlib import Path
from typing import Optional


class Config:
    """Класс для загрузки и управления конфигурацией сервиса"""

    DEFAULT_CONFIG = {
        "host": "127.0.0.1",
        "port": 8101,
        "default_printer": "",
        "api_key": "",
        "log_level": "INFO",
        "retry_count": 3,
    }

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self._validate_config()
        self._ensure_directories()

    def _load_config(self) -> dict:
        """Загрузка конфигурации из файла"""
        if not os.path.exists(self.config_path):
            self._save_default_config()
            return self.DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            for key, value in self.DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value

            return config
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга config.json: {e}")

    def _save_default_config(self):
        """Сохранение конфигурации по умолчанию"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)

    def _validate_config(self):
        """Валидация параметров конфигурации"""
        port = self.config.get("port")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError(f"Некорректный порт: {port}. Должен быть в диапазоне 1-65535")

        retry_count = self.config.get("retry_count")
        if not isinstance(retry_count, int) or retry_count < 0:
            raise ValueError(f"Некорректный retry_count: {retry_count}")

        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level = self.config.get("log_level", "INFO").upper()
        if log_level not in valid_log_levels:
            raise ValueError(f"Некорректный log_level: {log_level}. Доступные: {valid_log_levels}")
        self.config["log_level"] = log_level

    def _ensure_directories(self):
        """Создание необходимых директорий"""
        logs_folder = Path("./logs")
        logs_folder.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def set(self, key: str, value):
        self.config[key] = value

    def save(self):
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    @property
    def host(self) -> str:
        return self.config.get("host", "127.0.0.1")

    @property
    def port(self) -> int:
        return self.config.get("port", 8101)

    @property
    def default_printer(self) -> str:
        return self.config.get("default_printer", "")

    @property
    def api_key(self) -> str:
        return self.config.get("api_key", "")

    @property
    def log_level(self) -> str:
        return self.config.get("log_level", "INFO")

    @property
    def retry_count(self) -> int:
        return self.config.get("retry_count", 3)

    @property
    def requires_api_key(self) -> bool:
        return bool(self.api_key)


_config_instance: Optional[Config] = None


def get_config(config_path: str = "config.json") -> Config:
    """Получение глобального экземпляра конфигурации"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
