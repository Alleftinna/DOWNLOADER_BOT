# Генератор куков для платформ

Этот модуль автоматически генерирует куки для различных платформ каждые 12 часов.

## Поддерживаемые платформы

- **Instagram** - основные куки и bearer токены
- **Reddit** - client_id, client_secret, refresh_token
- **Twitter** - auth_token, ct0
- **YouTube** - cookie, b

## Структура файла cookies.json

```json
{
    "instagram": [
        "mid=<random>; ig_did=<random>; csrftoken=<random>; ds_user_id=<random>; sessionid=<random>"
    ],
    "instagram_bearer": [
        "token=<random_token>",
        "token=IGT:2:<random_format>"
    ],
    "reddit": [
        "client_id=<random>; client_secret=<random>; refresh_token=<random>"
    ],
    "twitter": [
        "auth_token=<random>; ct0=<random>"
    ],
    "youtube": [
        "cookie=<random>; b=<random>"
    ]
}
```

## Использование

### Автоматический запуск

Генератор куков автоматически запускается при старте основного бота (`main.py`) и работает в фоновом режиме.

### Ручной запуск

```bash
# Запуск генератора куков
python cookie_generator.py

# Тестирование генератора
python test_cookies.py
```

### Программное использование

```python
from cookie_generator import CookieGenerator

# Создание генератора
generator = CookieGenerator()

# Запуск автоматического обновления
generator.start()

# Принудительное обновление куков
cookies = generator.force_update()

# Остановка генератора
generator.stop()
```

## Настройка

### Интервал обновления

По умолчанию куки обновляются каждые 12 часов. Можно изменить при создании:

```python
generator = CookieGenerator(update_interval_hours=24)  # Обновление каждые 24 часа
```

### Файл куков

По умолчанию куки сохраняются в `cookies.json`. Можно указать другой файл:

```python
generator = CookieGenerator(cookies_file="my_cookies.json")
```

## Особенности

1. **Автоматическое обновление**: Куки обновляются каждые 12 часов в фоновом режиме
2. **Случайная генерация**: Все значения генерируются случайным образом
3. **Безопасность**: Используются криптографически стойкие случайные строки
4. **Логирование**: Все операции логируются с временными метками
5. **Обработка ошибок**: Автоматическое восстановление после ошибок

## Файлы

- `cookie_generator.py` - основной модуль генератора
- `test_cookies.py` - тестовый скрипт
- `cookies.json` - файл с сгенерированными куками (создается автоматически)

## Требования

- Python 3.7+
- Стандартные библиотеки Python (json, os, time, threading, random, string, datetime, pathlib)

## Интеграция с основным ботом

Генератор куков автоматически интегрирован в `main.py` и запускается при старте бота. Куки будут доступны в файле `cookies.json` для использования в других частях приложения.

## Настройка для Docker

### 1. Создание локальной директории

Перед запуском Docker контейнера создайте локальную директорию:

```bash
# Сделать скрипт исполняемым
chmod +x setup_cobalt_dir.sh

# Запустить скрипт создания директории
sudo ./setup_cobalt_dir.sh
```

### 2. Volume Mapping

В `docker-compose.yml` настроен volume mapping:
```yaml
volumes:
  - ./data:/app/data
  - /root/cobalt:/root/cobalt
```

Это означает, что директория `/root/cobalt` в контейнере будет синхронизирована с локальной директорией `/root/cobalt` на хосте.

### 3. Запуск

```bash
# Пересобрать и запустить контейнер
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 4. Проверка

Куки будут сохраняться в локальной директории `/root/cobalt/cookies.json` и автоматически обновляться каждые 12 часов.
