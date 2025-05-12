import requests
import json # Хотя requests обрабатывает json=data, импортируем для ясности

# --- Конфигурация запроса ---
# URL конечной точки API Alchemy
url = 'https://eth-sepolia.g.alchemy.com/v2/tzP8MzcTYkHb4SuKXPKk9Z9xa8Dwo5xg'

# Заголовки запроса, указывающие на формат JSON
headers = {
    'Content-Type': 'application/json'
}

# Тело запроса в формате JSON-RPC
# Запрашиваем ID цепочки (Chain ID)
data = {
    'jsonrpc': '2.0',
    'method': 'eth_chainId', # Метод JSON-RPC
    'params': [],            # Параметры для метода (в данном случае нет)
    'id': 1                  # Идентификатор запроса (может быть любым)
}

# Время ожидания ответа в секундах
timeout_seconds = 15 

# --- Выполнение запроса ---
print(f"Отправка HTTP POST запроса на: {url}...")
print(f"Данные запроса: {json.dumps(data)}") # Выводим отправляемые данные

try:
    # Выполняем POST-запрос с использованием библиотеки requests
    # - url: Куда отправляем запрос
    # - headers: Заголовки запроса
    # - json=data: Передаем словарь `data`, requests автоматически 
    #              сериализует его в JSON и установит Content-Type, 
    #              даже если он уже есть в headers.
    # - timeout: Максимальное время ожидания ответа
    response = requests.post(url, headers=headers, json=data, timeout=timeout_seconds)

    # --- Обработка ответа ---
    print(f"Статус HTTP ответа: {response.status_code}")

    # Выводим первые 200 символов текста ответа для краткости
    # Проверяем, есть ли вообще текст в ответе
    response_text = response.text
    if response_text:
      print(f"Тело ответа (первые 200 символов): {response_text[:200]}...")
    else:
      print("Тело ответа пустое.")

    # Дополнительно: можно проверить статус код на ошибки
    # response.raise_for_status() # Вызовет исключение для кодов 4xx/5xx

    # Дополнительно: если ожидается JSON, можно его распарсить
    # try:
    #     response_json = response.json()
    #     print(f"Ответ в формате JSON: {response_json}")
    # except requests.exceptions.JSONDecodeError:
    #     print("Не удалось декодировать ответ как JSON.")
        
except requests.exceptions.Timeout:
    # Ошибка: время ожидания истекло
    print(f"HTTP FAIL: Запрос превысил таймаут ({timeout_seconds} сек).")
    
except requests.exceptions.ConnectionError as e:
    # Ошибка: проблема с соединением (DNS, сеть недоступна и т.д.)
    print(f"HTTP FAIL: Ошибка соединения.")
    print(f"  Тип ошибки: {type(e).__name__}")
    print(f"  Детали: {e}")

except requests.exceptions.RequestException as e:
    # Обработка других ошибок, связанных с requests (неверный URL, SSL и т.д.)
    print(f"HTTP FAIL: Произошла ошибка при выполнении запроса.")
    print(f"  Тип ошибки: {type(e).__name__}")
    print(f"  Детали: {e}")

except Exception as e:
    # Обработка любых других непредвиденных ошибок
    print(f"HTTP FAIL: Произошла непредвиденная ошибка.")
    print(f"  Тип ошибки: {type(e).__name__}")
    print(f"  Детали: {e}")