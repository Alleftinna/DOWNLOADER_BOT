# Телеграм бот для скачивания видео

Телеграм бот скачивает видео через отдельный сервис на **yt-dlp** (Flask API в каталоге `downloader/`).

## Особенности

- Скачивает видео с множества платформ: YouTube, TikTok, Instagram, Facebook, Twitter, Vimeo, Bilibili, Bluesky, Dailymotion, Reddit, Twitch и др.
- Использует aiogram 3+ для работы с Telegram API
- Работает в режиме поллинга
- Автоматически удаляет видео после отправки пользователю
- Контейнеризирован с помощью Docker для простого развертывания

## Установка

1. Клонируйте этот репозиторий
2. Скопируйте `.env.example` в `.env` и заполните токен вашего Телеграм бота:
   ```bash
   cp .env.example .env
   ```
3. Отредактируйте файл `.env` вашими настоящими конфигурационными значениями
4. Соберите и запустите стек (бот + `downloader`):
   ```bash
   docker compose up -d
   ```

## Переменные окружения

- `BOT_TOKEN`: токен бота от BotFather
- `DOWNLOADER_API_URL`: базовый URL Flask-сервиса (в Compose задаётся как `http://downloader:8899`)
- `DOWNLOAD_POLL_INTERVAL`, `DOWNLOAD_MAX_WAIT`: опрос `/api/status` и таймаут ожидания задачи (секунды)

## Использование

1. Начните чат с вашим ботом в Телеграме
2. Отправьте ссылку на видео с поддерживаемой платформы
3. Бот скачает видео и отправит его вам обратно

## Поддерживаемые платформы

- YouTube
- TikTok
- Instagram
- Facebook
- Twitter/X
- Vimeo
- Bilibili
- Bluesky
- Dailymotion
- Loom
- OK.ru
- Pinterest
- Reddit
- Rutube
- Snapchat
- SoundCloud
- Streamable
- Tumblr
- Twitch
- VK
- Xiaohongshu

## Разработка

Для локального запуска бота для разработки:

```bash
# Установите зависимости
pip install -r requirements.txt

# Запустите бота
python main.py
```

## Лицензия

MIT 