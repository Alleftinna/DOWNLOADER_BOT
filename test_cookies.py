#!/usr/bin/env python3
"""
Тестовый скрипт для генератора куков
"""

from cookie_generator import CookieGenerator, get_cookies_save_path, set_cookies_save_path
import json
import time

def test_cookie_generation():
    """Тестирует генерацию куков"""
    print("=== Тестирование генератора куков ===\n")
    
    # Создаем генератор
    generator = CookieGenerator()
    
    # Генерируем куки
    print("Генерирую новые куки...")
    cookies = generator.generate_all_cookies()
    
    # Выводим результат
    print("Сгенерированные куки:")
    print(json.dumps(cookies, indent=4, ensure_ascii=False))
    
    # Сохраняем в файл
    print(f"\nСохраняю куки в файл {generator.cookies_file}...")
    generator.save_cookies(cookies)
    
    # Загружаем обратно для проверки
    print("Загружаю куки из файла для проверки...")
    loaded_cookies = generator.load_cookies()
    
    if loaded_cookies == cookies:
        print("✅ Куки успешно сохранены и загружены!")
    else:
        print("❌ Ошибка при сохранении/загрузке куков")
    
    return cookies

def test_individual_platforms():
    """Тестирует генерацию куков для отдельных платформ"""
    print("\n=== Тестирование отдельных платформ ===\n")
    
    generator = CookieGenerator()
    
    platforms = [
        ("Instagram", generator.generate_instagram_cookies),
        ("Instagram Bearer", generator.generate_instagram_bearer_tokens),
        ("Reddit", generator.generate_reddit_cookies),
        ("Twitter", generator.generate_twitter_cookies),
        ("YouTube", generator.generate_youtube_cookies)
    ]
    
    for platform_name, generator_func in platforms:
        print(f"{platform_name}:")
        try:
            result = generator_func()
            print(f"  ✅ {result[:50]}...")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
        print()

def test_global_path():
    """Тестирует работу с глобальным путем"""
    print("\n=== Тестирование глобального пути ===\n")
    
    # Получаем текущий путь
    current_path = get_cookies_save_path()
    print(f"Текущий глобальный путь: {current_path}")
    
    # Создаем генератор с глобальным путем по умолчанию
    generator1 = CookieGenerator()
    print(f"Генератор 1 путь: {generator1.get_save_path()}")
    
    # Создаем генератор с кастомным путем
    custom_path = "custom_cookies.json"
    generator2 = CookieGenerator(cookies_file=custom_path)
    print(f"Генератор 2 путь: {generator2.get_save_path()}")
    
    # Изменяем путь генератора 2
    new_path = "new_cookies.json"
    generator2.set_save_path(new_path)
    print(f"Генератор 2 новый путь: {generator2.get_save_path()}")
    
    # Изменяем глобальный путь
    new_global_path = "global_cookies.json"
    set_cookies_save_path(new_global_path)
    print(f"Новый глобальный путь: {get_cookies_save_path()}")
    
    # Создаем генератор 3 с новым глобальным путем
    generator3 = CookieGenerator()
    print(f"Генератор 3 путь: {generator3.get_save_path()}")
    
    # Возвращаем исходный глобальный путь
    set_cookies_save_path(current_path)
    print(f"Восстановлен исходный глобальный путь: {get_cookies_save_path()}")

if __name__ == "__main__":
    try:
        # Тестируем генерацию всех куков
        test_cookie_generation()
        
        # Тестируем отдельные платформы
        test_individual_platforms()
        
        print("=== Все тесты завершены ===")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
