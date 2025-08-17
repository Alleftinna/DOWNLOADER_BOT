import json
import os
import time
import threading
import random
import string
from datetime import datetime

# Глобальный путь для сохранения куков
COOKIES_SAVE_PATH = "/root/cobalt/cookies.json"

def get_cookies_save_path():
    """Возвращает текущий глобальный путь для сохранения куков"""
    return COOKIES_SAVE_PATH

def set_cookies_save_path(new_path):
    """Устанавливает новый глобальный путь для сохранения куков"""
    global COOKIES_SAVE_PATH
    COOKIES_SAVE_PATH = new_path
    return COOKIES_SAVE_PATH


class CookieGenerator:
    def __init__(self, cookies_file=None, update_interval_hours=12):
        # Используем глобальный путь по умолчанию, если не указан другой
        self.cookies_file = cookies_file if cookies_file else COOKIES_SAVE_PATH
        self.update_interval_hours = update_interval_hours
        self.running = False
        self.thread = None
        
    def generate_random_string(self, length=32):
        """Генерирует случайную строку указанной длины"""
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))
    
    def generate_random_hex(self, length=32):
        """Генерирует случайную hex строку указанной длины"""
        return ''.join(random.choice('0123456789abcdef') for _ in range(length))
    
    def generate_instagram_cookies(self):
        """Генерирует куки для Instagram"""
        mid = self.generate_random_string(24)
        ig_did = self.generate_random_hex(32)
        csrftoken = self.generate_random_string(32)
        ds_user_id = str(random.randint(100000000, 999999999))
        sessionid = self.generate_random_string(32)
        
        return f"mid={mid}; ig_did={ig_did}; csrftoken={csrftoken}; ds_user_id={ds_user_id}; sessionid={sessionid}"
    
    def generate_instagram_bearer_tokens(self):
        """Генерирует bearer токены для Instagram"""
        token1 = self.generate_random_string(40)
        token2 = f"IGT:2:{self.generate_random_string(32)}"
        
        return [f"token={token1}", f"token={token2}"]
    
    def generate_reddit_cookies(self):
        """Генерирует куки для Reddit"""
        client_id = self.generate_random_string(22)
        client_secret = self.generate_random_string(27)
        refresh_token = self.generate_random_string(43)
        
        return f"client_id={client_id}; client_secret={client_secret}; refresh_token={refresh_token}"
    
    def generate_twitter_cookies(self):
        """Генерирует куки для Twitter"""
        auth_token = self.generate_random_string(32)
        ct0 = self.generate_random_string(32)
        
        return f"auth_token={auth_token}; ct0={ct0}"
    
    def generate_youtube_cookies(self):
        """Генерирует куки для YouTube"""
        cookie = self.generate_random_string(40)
        b = self.generate_random_string(20)
        
        return f"cookie={cookie}; b={b}"
    
    def generate_all_cookies(self):
        """Генерирует все куки для всех платформ"""
        cookies = {
            "instagram": [
                self.generate_instagram_cookies()
            ],
            "instagram_bearer": self.generate_instagram_bearer_tokens(),
            "reddit": [
                self.generate_reddit_cookies()
            ],
            "twitter": [
                self.generate_twitter_cookies()
            ],
            "youtube": [
                self.generate_youtube_cookies()
            ]
        }
        return cookies
    
    def save_cookies(self, cookies):
        """Сохраняет куки в файл"""
        try:
            with open(self.cookies_file, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=4, ensure_ascii=False)
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Куки обновлены и сохранены в {self.cookies_file}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка при сохранении куков: {e}")
    
    def load_cookies(self):
        """Загружает куки из файла"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Файл {self.cookies_file} не найден. Создаю новые куки...")
                return None
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка при загрузке куков: {e}")
            return None
    
    def update_cookies(self):
        """Обновляет куки"""
        cookies = self.generate_all_cookies()
        self.save_cookies(cookies)
        return cookies
    
    def cookie_update_worker(self):
        """Рабочий поток для обновления куков"""
        while self.running:
            try:
                # Обновляем куки
                self.update_cookies()
                
                # Ждем указанное время
                time.sleep(self.update_interval_hours * 3600)
            except Exception as e:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка в рабочем потоке: {e}")
                time.sleep(60)  # Ждем минуту перед повторной попыткой
    
    def start(self):
        """Запускает генератор куков"""
        if self.running:
            print("Генератор куков уже запущен")
            return
        
        # Проверяем, нужно ли создать новые куки
        existing_cookies = self.load_cookies()
        if existing_cookies is None:
            # Создаем новые куки при первом запуске
            self.update_cookies()
        
        self.running = True
        self.thread = threading.Thread(target=self.cookie_update_worker, daemon=True)
        self.thread.start()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Генератор куков запущен. Обновление каждые {self.update_interval_hours} часов.")
    
    def stop(self):
        """Останавливает генератор куков"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Генератор куков остановлен")
    
    def force_update(self):
        """Принудительно обновляет куки"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Принудительное обновление куков...")
        return self.update_cookies()
    
    def get_save_path(self):
        """Возвращает текущий путь сохранения куков"""
        return self.cookies_file
    
    def set_save_path(self, new_path):
        """Устанавливает новый путь сохранения куков"""
        self.cookies_file = new_path
        return self.cookies_file

def main():
    """Основная функция для тестирования"""
    generator = CookieGenerator()
    
    try:
        # Запускаем генератор
        generator.start()
        
        # Ждем немного для демонстрации
        print("Генератор запущен. Нажмите Ctrl+C для остановки...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки...")
        generator.stop()
        print("Генератор остановлен")

if __name__ == "__main__":
    main()
