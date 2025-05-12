# oracle-backend/app_ui.py
import streamlit as st
import requests # Для HTTP запросов к нашему FastAPI бэкенду
import time
import pandas as pd # Для красивого отображения таблиц
import os


st.set_page_config(page_title="Oracle Dashboard", layout="wide")

# URL нашего FastAPI бэкенда
BACKEND_URL = os.getenv("BACKEND_SERVICE_URL", "http://127.0.0.1:8000")
st.sidebar.markdown(f"Backend: {BACKEND_URL}") # Для отладки

# st.set_page_config(page_title="Oracle Dashboard", layout="wide")

st.title("📊 Панель управления Оракулом Цен")

# --- Функция для получения данных с бэкенда ---
def get_data_from_backend(endpoint: str):
    try:
        response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
        response.raise_for_status() # Вызовет ошибку, если статус не 2xx
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ошибка при подключении к бэкенду ({endpoint}): {e}")
        return None
    except json.JSONDecodeError:
        st.error(f"Ошибка при декодировании JSON ответа от {endpoint}")
        return None

# --- Отображение статуса ---
st.header("📈 Общий Статус Оракула")
status_data = get_data_from_backend("/status")

if status_data:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Отслеживаемые пары:")
        for pair in status_data.get("tracked_pairs", []):
            st.markdown(f"- `{pair}`")
        st.metric("Интервал опроса Binance", f"{status_data.get('binance_polling_interval_seconds', 'N/A')} сек")

    with col2:
        st.subheader("Статус Event Listener'а:")
        listener_status = status_data.get("event_listener", {})
        st.metric("Активен", "✅ Да" if listener_status.get("active") else "❌ Нет")
        st.metric("Подключен к Web3", "✅ Да" if listener_status.get("web3_connected") else "❌ Нет")
        st.markdown(f"**Chain ID:** `{listener_status.get('chain_id', 'N/A')}`")
        st.markdown(f"**Адрес контракта Оракула:** `{listener_status.get('contract_address', 'N/A')}`")
        st.markdown(f"**Адрес подписанта Оракула:** `{listener_status.get('signer_address', 'N/A')}`")
else:
    st.warning("Не удалось загрузить статус оракула.")

st.divider()

# --- Отображение последних цен ---
st.header("💹 Последние полученные цены (с Binance)")
if status_data and "latest_prices" in status_data:
    prices_to_display = []
    for pair, data in status_data["latest_prices"].items():
        if data:
            prices_to_display.append({
                "Пара": pair,
                "Цена": data.get("price", "N/A"),
                "Timestamp": pd.to_datetime(data.get("timestamp", 0), unit='s').strftime('%Y-%m-%d %H:%M:%S') if data.get("timestamp") else "N/A"
            })
        else:
            prices_to_display.append({"Пара": pair, "Цена": "N/A", "Timestamp": "N/A"})

    if prices_to_display:
        df_prices = pd.DataFrame(prices_to_display)
        st.dataframe(df_prices, use_container_width=True, hide_index=True)
    else:
        st.info("Данные о ценах пока отсутствуют.")
else:
    st.info("Данные о последних ценах не загружены.")

st.divider()

# --- Запрос подписанной цены ---
st.header("✍️ Запросить Подписанную Цену (Оффчейн)")

if status_data and "tracked_pairs" in status_data:
    selected_pair_for_signature = st.selectbox(
        "Выберите пару для получения подписанной цены:",
        options=status_data["tracked_pairs"],
        key="select_signed_price"
    )

    if st.button("Получить подписанную цену", key="btn_get_signed_price"):
        if selected_pair_for_signature:
            # Преобразуем пару для URL (BTC/USDT -> BTC-USDT)
            api_pair = selected_pair_for_signature.replace('/', '-')
            signed_price_data = get_data_from_backend(f"/signed_price/{api_pair}")
            if signed_price_data:
                st.subheader(f"Подписанные данные для {signed_price_data.get('assetPair')}:")
                st.json(signed_price_data) # Отображаем весь JSON
                # Можно и детальнее:
                # st.markdown(f"**Цена:** `{signed_price_data.get('price')}`")
                # st.markdown(f"**Timestamp:** `{pd.to_datetime(signed_price_data.get('timestamp'), unit='s').strftime('%Y-%m-%d %H:%M:%S')}`")
                # st.markdown(f"**Asset ID (hex):** `{signed_price_data.get('assetId')}`")
                # st.markdown(f"**Подпись (hex):**")
                # st.code(signed_price_data.get('signature', ''), language=None)
            else:
                st.error(f"Не удалось получить подписанную цену для {selected_pair_for_signature}.")
else:
    st.info("Список отслеживаемых пар не загружен, невозможно запросить подписанную цену.")


# --- Автообновление (опционально) ---
# st.write("Страница будет автоматически обновляться каждые 15 секунд.")
# time.sleep(15) # Осторожно, это блокирующий вызов
# st.experimental_rerun()

# Можно добавить в конце, чтобы видеть "живые" данные, если бэкенд работает
st.sidebar.button("Обновить данные", on_click=st.rerun)

st.caption("Простой UI для демонстрации работы Оракула")