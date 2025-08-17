# Телеграм бот для скачивания видео

Телеграм бот, который скачивает видео с различных платформ с использованием сервиса Cobalt.

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
4. Соберите и запустите контейнер:
   ```bash
   docker-compose up -d
   ```

## Переменные окружения

- `BOT_TOKEN`: Токен вашего Телеграм бота от BotFather
- `COBALT_API_URL`: URL сервиса Cobalt (по умолчанию: http://31.128.33.148:9000)
- `COBALT_API_KEY`: API ключ для сервиса Cobalt (если требуется)

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