#!/bin/bash

# Скрипт для создания локальной директории cobalt

echo "Создаю директорию /root/cobalt для сохранения куков..."

# Создаем директорию с правами root
sudo mkdir -p /root/cobalt

# Устанавливаем правильные права доступа
sudo chown root:root /root/cobalt
sudo chmod 755 /root/cobalt

echo "Директория /root/cobalt создана успешно!"
echo "Теперь можно запускать Docker контейнер с volume mapping."

# Проверяем, что директория создана
if [ -d "/root/cobalt" ]; then
    echo "✅ Директория /root/cobalt существует"
    ls -la /root/cobalt
else
    echo "❌ Ошибка: директория не создана"
fi
