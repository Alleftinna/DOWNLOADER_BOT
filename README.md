# Телеграм бот для скачивания видео

Телеграм бот скачивает видео через Cobalt API, а если Cobalt не смог обработать ссылку, автоматически переключается на fallback downloader на базе `yt-dlp`.

## Архитектура

- `cobalt-bot` — Telegram bot на `aiogram`, основная точка входа `main.py`.
- `downloader` — отдельный Flask-сервис с `yt-dlp`, используется как fallback.
- `cobalt-api` — основной downloader backend. Он запускается отдельно и должен быть доступен в external Docker network.

## Запуск в Docker

Скопируйте `.env.example` в `.env` и заполните `BOT_TOKEN`:

```bash
cp .env.example .env
```

Убедитесь, что контейнер Cobalt подключён к external network `cobalt-network` и доступен по имени `cobalt-api` на порту `9000`.

Запуск бота и fallback downloader:

```bash
docker compose up -d --build
```

## Переменные окружения

- `BOT_TOKEN` — токен Telegram бота от BotFather.
- `COBALT_API_URL` — URL Cobalt API внутри Docker-сети, по умолчанию `http://cobalt-api:9000`.
- `COBALT_API_KEY` — API key для Cobalt, если он включён.
- `DOWNLOADER_URL` — URL fallback downloader, по умолчанию `http://downloader:8899`.
- `VIDEO_QUALITY` — целевое качество видео, по умолчанию `480`.
- `RESTRICTED_THREADS` — список topic/thread id через запятую, которые бот игнорирует.

## Локальная разработка

Если бот запускается не в Docker, а Cobalt проброшен на хост-машину:

```bash
COBALT_API_URL=http://localhost:9000 python main.py
```

Fallback downloader можно запустить отдельно:

```bash
HOST=0.0.0.0 PORT=8899 python -m downloader.app
```

## Поддерживаемые платформы

YouTube, TikTok, Instagram, Facebook, Twitter/X, Vimeo, Bilibili, Bluesky, Dailymotion, Loom, OK.ru, Pinterest, Reddit, Rutube, Snapchat, SoundCloud, Streamable, Tumblr, Twitch, VK, Xiaohongshu.