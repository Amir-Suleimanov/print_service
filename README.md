# Print Service для Windows 7/10

Фоновый Windows-сервис для автоматической печати документов через REST API.

## Возможности

- ✅ REST API для отправки файлов на печать
- ✅ Поддержка PDF, изображений (PNG, JPG, BMP, TIFF)
- ✅ Печать из base64 строк
- ✅ Очередь печати с автоматическими повторными попытками
- ✅ Работа как Windows Service с автозапуском
- ✅ Управление принтерами
- ✅ Мониторинг статуса заданий

## Требования

- Windows 7 / Windows 10
- Python 3.7+
- Права администратора (для установки сервиса)

## Установка

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

**Важно для Windows 7**: После установки `pywin32` выполните:
```bash
python C:\Python3X\Scripts\pywin32_postinstall.py -install
```
(Замените `C:\Python3X` на путь к вашему Python)

### 2. Настройка конфигурации

Отредактируйте `config.json`:

```json
{
  "host": "127.0.0.1",
  "port": 8101,
  "default_printer": "",
  "max_file_size_mb": 50,
  "api_key": "",
  "log_level": "INFO",
  "retry_count": 3,
  "temp_folder": "./temp"
}
```

### 3. Установка Windows Service

**Запустите cmd от имени администратора:**

```bash
# Установка сервиса
python install_service.py install

# Запуск сервиса
python install_service.py start

# Проверка статуса
python install_service.py status
```

Сервис будет автоматически запускаться при старте Windows.

## Использование

### API Эндпоинты

#### 1. Проверка работоспособности

```bash
curl http://127.0.0.1:8101/api/health
```

#### 2. Получение списка принтеров

```bash
curl http://127.0.0.1:8101/api/printers
```

Ответ:
```json
{
  "success": true,
  "printers": [
    {
      "name": "Microsoft Print to PDF",
      "status": "Ready",
      "is_default": true
    }
  ],
  "count": 1
}
```

#### 3. Печать файла

**Печать локального файла:**
```bash
curl -X POST http://127.0.0.1:8101/api/print \
  -H "Content-Type: application/json" \
  -d "{\"type\": \"file\", \"data\": \"C:\\\\path\\\\to\\\\document.pdf\", \"format\": \"pdf\", \"copies\": 1}"
```

**Печать из base64:**
```bash
curl -X POST http://127.0.0.1:8101/api/print \
  -H "Content-Type: application/json" \
  -d "{\"type\": \"base64\", \"data\": \"JVBERi0xLjQK...\", \"format\": \"auto\", \"printer\": \"HP LaserJet\"}"
```

**Упрощённый эндпоинт для base64 изображения (`jpeg`):**
```bash
curl -X POST http://127.0.0.1:8101/api/print/simple \
  -H "Content-Type: application/json" \
  -d "{\"jpeg\": \"iVBORw0KGgoAAAANSUhEUgAA...\", \"printer\": \"HP LaserJet\"}"
```

**С опциями:**
```bash
curl -X POST http://127.0.0.1:8101/api/print \
  -H "Content-Type: application/json" \
  -d "{\"type\": \"file\", \"data\": \"document.pdf\", \"copies\": 2, \"options\": {\"orientation\": \"landscape\", \"paper_size\": \"A4\"}}"
```

Ответ:
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Задание отправлено в очередь печати"
}
```

#### 4. Проверка статуса задания

```bash
curl http://127.0.0.1:8101/api/status/550e8400-e29b-41d4-a716-446655440000
```

Ответ:
```json
{
  "success": true,
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "created_at": "2026-02-05T15:30:00",
  "updated_at": "2026-02-05T15:30:05",
  "error_message": null
}
```

Возможные статусы:
- `pending` - в очереди
- `processing` - печатается
- `completed` - выполнено
- `failed` - ошибка
- `cancelled` - отменено

#### 5. Отмена задания

```bash
curl -X DELETE http://127.0.0.1:8101/api/cancel/550e8400-e29b-41d4-a716-446655440000
```

#### 6. Просмотр очереди

```bash
curl http://127.0.0.1:8101/api/queue
```

### Примеры использования (Python)

```python
import requests
import base64

# URL сервиса
BASE_URL = "http://127.0.0.1:8101/api"

# 1. Проверка принтеров
response = requests.get(f"{BASE_URL}/printers")
printers = response.json()
print(printers)

# 2. Печать локального файла
data = {
    "type": "file",
    "data": "C:\\Documents\\report.pdf",
    "format": "pdf",
    "copies": 1
}
response = requests.post(f"{BASE_URL}/print", json=data)
result = response.json()
job_id = result['job_id']
print(f"Job ID: {job_id}")

# 3. Печать из base64
with open("image.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

data = {
    "type": "base64",
    "data": image_data,
    "format": "image",
    "printer": "HP LaserJet"
}
response = requests.post(f"{BASE_URL}/print", json=data)
print(response.json())

# 3.1 Упрощённая печать base64 изображения
data = {
    "jpeg": image_data,
    "printer": "HP LaserJet"
}
response = requests.post(f"{BASE_URL}/print/simple", json=data)
print(response.json())

# 4. Проверка статуса
response = requests.get(f"{BASE_URL}/status/{job_id}")
status = response.json()
print(f"Status: {status['status']}")
```

## Управление сервисом

```bash
# Запуск сервиса
python install_service.py start

# Остановка сервиса
python install_service.py stop

# Перезапуск сервиса
python install_service.py restart

# Проверка статуса
python install_service.py status

# Удаление сервиса
python install_service.py remove
```

Также можно управлять через:
- **services.msc** (Службы Windows)
- `sc` команды в cmd

## Безопасность

### API Key (опционально)

Для защиты API установите ключ в `config.json`:

```json
{
  "api_key": "your-secret-key-here"
}
```

Затем передавайте ключ в запросах:

```bash
# В заголовке
curl -H "X-API-Key: your-secret-key-here" http://127.0.0.1:8101/api/printers

# Или в параметре
curl http://127.0.0.1:8101/api/printers?api_key=your-secret-key-here
```

### Доступ из сети

По умолчанию сервис слушает только `127.0.0.1` (localhost). Для доступа из сети измените в `config.json`:

```json
{
  "host": "0.0.0.0"
}
```

**Внимание:** Откройте порт в Windows Firewall и используйте API key!

## Логи

Логи сохраняются в `./logs/YYYY-MM-DD.log`:
- Каждый день создаётся отдельный файл с текущей датой
- Хранение: 7 дней

Для просмотра логов в реальном времени:
```bash
tail -f logs/$(date +%F).log
```

(Или используйте PowerShell: `Get-Content -Path logs/$(Get-Date -Format yyyy-MM-dd).log -Wait`)

## Troubleshooting

### Сервис не запускается

1. Проверьте Event Viewer → Windows Logs → Application
2. Проверьте логи в `./logs/YYYY-MM-DD.log`
3. Убедитесь что порт 8101 свободен:
   ```bash
   netstat -ano | findstr 8101
   ```

### Ошибка "Принтер не найден"

Проверьте список принтеров:
```bash
curl http://127.0.0.1:8101/api/printers
```

Используйте точное имя принтера из списка.

### Ошибки печати изображений

Некоторые форматы изображений могут требовать конвертации. Сервис автоматически попытается конвертировать в PDF.

### Windows 7: pywin32 не работает

После установки pywin32 обязательно выполните:
```bash
python Scripts/pywin32_postinstall.py -install
```

## Структура проекта

```
print_service/
├── main.py              # Точка входа приложения
├── service.py           # Windows Service wrapper
├── install_service.py   # Скрипт установки сервиса
├── config.py            # Управление конфигурацией
├── config.json          # Конфигурация
├── requirements.txt     # Зависимости
├── api/
│   ├── routes.py        # REST API эндпоинты
│   └── validators.py    # Валидация запросов (Pydantic)
├── services/
│   ├── printer.py       # Работа с принтерами (win32print)
│   ├── converter.py     # Конвертация форматов
│   └── queue.py         # Очередь печати
├── utils/
│   └── logger.py        # Логирование (loguru)
├── temp/                # Временные файлы
└── logs/                # Логи
```

## Лицензия

MIT License

## Поддержка

Для вопросов и багов создайте issue в репозитории.
# print_service
