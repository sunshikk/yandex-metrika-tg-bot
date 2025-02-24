import logging
import asyncio
import os
import string
import requests

from datetime import datetime

from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

class Form(StatesGroup):
    date1 = State()
    date2 = State()
    date1utm = State()
    date2utm = State()

choicestart = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📊 Просмотр статистики сайта за определенный период", callback_data="checkstat")],
    [InlineKeyboardButton(text="📊 Просмотр статистики сайта с UTM метками", callback_data="checkstatutm")]
]) # Кнопки

choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="1️⃣ Вчера", callback_data="yesterday")],
    [InlineKeyboardButton(text="2️⃣ Неделя", callback_data="week")],
    [InlineKeyboardButton(text="3️⃣ Месяц", callback_data="month")],
    [InlineKeyboardButton(text="🔄 Указать другой промежуток", callback_data="otherdate")]
])

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["TOKEN"]

bot = Bot(token=BOT_TOKEN) # токен, который будет в качестве переменной на хостинге
dp = Dispatcher() # переменная диспетчера
router = Router() # переменная роутера
YANDEX_METRIKA_TOKEN = os.environ["TOKEN_YANDEX"]
COUNTER_ID = os.environ["COUNTER_ID"]

choicestat = None

start_date = datetime.today().replace(day=1).strftime("%Y-%m-%d")
end_date = datetime.today().strftime("%Y-%m-%d")

# Определяем класс для работы с API Яндекс Метрики
class YandexMetrica:
    def __init__(self, token):  # Конструктор класса, принимающий токен API
        self.token = token  # Сохраняем токен в объекте
        self.base_url = "https://api-metrika.yandex.net/stat/v1/data"  # Базовый URL API

    def get_data(self, counter_id, params):  # Метод для получения данных
        headers = {  # Заголовки запроса
            "Authorization": f"OAuth {self.token}"  # Передаём токен в заголовке
        }
        params['ids'] = counter_id  # Добавляем ID счетчика в параметры запроса
        response = requests.get(self.base_url, headers=headers, params=params)  # Отправляем GET-запрос
        print(response)  # Выводим объект ответа в консоль

        if response.status_code == 200:  # Если запрос успешен (код 200)
            return response.json()  # Возвращаем JSON-ответ
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")  # Логируем ошибку
            if response.status_code == 403:  # Если ошибка 403 (доступ запрещён)
                logging.error("Access Denied: Проверьте токен и права доступа к счетчику.")  # Выводим сообщение
            return None  # Возвращаем None в случае ошибки

# Функция для проверки, является ли строка датой

def is_date(text):
    allowed_chars = string.digits + "-"  # Разрешённые символы (цифры и дефис)
    for char in text:  # Перебираем символы в строке
        if char not in allowed_chars:  # Если символ не входит в список разрешённых
            return False  # Возвращаем False
    return True  # Если всё ок, возвращаем True

@router.message(CommandStart())  # Хэндлер для команды /start
async def start_command(message: types.Message):
    await message.answer("🤖 Это бот для работы с Яндекс Метрикой. Нажми на подходящую кнопку для запроса статистики.", reply_markup=choicestart)  # Отправляем приветственное сообщение

# Хэндлер для получения первой даты (начало периода)
@router.message(Form.date1)
async def date1(message: types.Message, state: FSMContext):
    if is_date(message.text):  # Проверяем, является ли введённый текст датой
        await state.update_data(date1=message.text)  # Сохраняем дату в состояние
        await state.set_state(Form.date2)  # Устанавливаем следующее состояние
        await message.answer("✍️ Отправьте дату по какое число, месяц и год нужна статистика (пример: 2025-02-28)")  # Запрашиваем вторую дату
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")  # Сообщаем об ошибке ввода

# Аналогичный хэндлер, но для UTM-меток
@router.message(Form.date1utm)
async def date1utm(message: types.Message, state: FSMContext):
    if is_date(message.text):  # Проверяем дату
        await state.update_data(date1utm=message.text)  # Сохраняем в state
        await state.set_state(Form.date2utm)  # Переключаем состояние
        await message.answer("✍️ Отправьте дату по какое число, месяц и год нужна статистика (пример: 2025-02-28)")
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")

# Хэндлер для получения второй даты и запроса статистики
@router.message(Form.date2)
async def date2(message: types.Message, state: FSMContext):
    dataaa = await state.get_data()  # Получаем сохранённые данные
    if is_date(message.text):  # Проверяем дату
        metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)  # Создаём объект API

        params = {
            "ids": COUNTER_ID,
            "metrics": "ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:newUsers,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
            "date1": dataaa.get('date1'),
            "date2": message.text,
            "accuracy": "full"
        }

        data = metrika.get_data(COUNTER_ID, params)  # Запрашиваем данные
        print("Raw data from Yandex Metrica:")
        print(data)  # Выводим в консоль полученные данные

        response_text = ""  # Строка ответа

        if data and data['data']:  # Если данные получены
            report_data = data['data'][0]
            
            metrics_data = report_data.get('metrics')  # Достаём метрики
            if metrics_data and isinstance(metrics_data, list):  # Проверяем формат данных
                visits = metrics_data[0] if len(metrics_data) > 0 else 0  # Извлекаем метрики
                pageviews = metrics_data[1] if len(metrics_data) > 1 else 0
                users = metrics_data[2] if len(metrics_data) > 2 else 0
                new_users = metrics_data[3] if len(metrics_data) > 3 else 0
                bounce_rate = metrics_data[4] if len(metrics_data) > 4 else 0
                avg_duration = metrics_data[5] if len(metrics_data) > 5 else 0
                
                response_text = (
                    f"📊 Статистика за промежуток: {dataaa.get('date1')} - {message.text}\n\n"
                    f"👁 Посещения: {int(visits)}\n"
                    f"📄 Просмотры страниц: {int(pageviews)}\n"
                    f"👤 Пользователи: {int(users)}\n"
                    f"🆕 Новые пользователи: {int(new_users)}\n"
                    f"📉 Процент отказов: {bounce_rate:.2f}%\n"
                    f"⏱️ Средняя длительность визита: {int(avg_duration // 60)} мин {int(avg_duration % 60)} сек\n\n"
                )
            else:
                response_text = "❌ Неверный формат данных статистики.\n"
        else:
            response_text = "❌ Не удалось получить данные статистики.\n"
        
        await message.answer(response_text)  # Отправляем ответ пользователю
        await state.clear()  # Очищаем состояние
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")  # Ошибка ввода

@router.message(Form.date2utm)
async def date2utm(message: types.Message, state: FSMContext):
    dataaa = await state.get_data()
    if is_date(message.text):
        metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)

        params = {
            "ids": COUNTER_ID,
            "metrics": "ym:s:visits",
            "dimensions": "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign",
            "date1": dataaa.get('date1utm'),
            "date2": message.text,
            "accuracy": "full"
        }

        data = metrika.get_data(COUNTER_ID, params)
        print("Raw data from Yandex Metrica:")
        print(data)

        response_text = ""

        # --- Сводка по UTM меткам ---
        utm_summary_text = " 📊 Сводка по UTM меткам:\n"
        utm_data_found = False

        if data and data['data']:
            for row in data['data']:
                if 'dimensions' in row and 'metrics' in row:
                    dimensions = row['dimensions']
                    metrics = row['metrics']

                    print("DEBUG: dimensions =", dimensions)  # Отладочный вывод

                    utm_source = "N/A"
                    utm_medium = "N/A"
                    utm_campaign = "N/A"

                    if dimensions:  # Проверяем, что dimensions не пустой
                        utm_source = dimensions[0].get('name', 'N/A') if len(dimensions) > 0 else "N/A"
                        utm_medium = dimensions[1].get('name', 'N/A') if len(dimensions) > 1 else "N/A"
                        utm_campaign = dimensions[2].get('name', 'N/A') if len(dimensions) > 2 else "N/A"

                    visits_utm = metrics[0] if metrics else 0
                    utm_summary_text += f"- 🔗 Источник: {utm_source}, 📡 Канал: {utm_medium}, 🎯 Кампания: {utm_campaign} - 👁 Посещения: {int(visits_utm)}\n"
                    utm_data_found = True

            if utm_data_found:
                response_text += utm_summary_text
        else:
            response_text = "❌ Не удалось получить данные статистики.\n"
            print("Ошибка: Не удалось получить данные из data['data']")

        await message.answer(response_text)
        await state.clear()
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")

async def date21(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)  # Создаём объект API

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:newUsers,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
        "date1": "1daysAgo", # Дата со вчерашнего дня
        "date2": "today",
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)  # Запрашиваем данные
    print("Raw data from Yandex Metrica:")
    print(data)  # Выводим в консоль полученные данные

    response_text = ""  # Строка ответа

    if data and data['data']:  # Если данные получены
        report_data = data['data'][0]
        
        metrics_data = report_data.get('metrics')  # Достаём метрики
        if metrics_data and isinstance(metrics_data, list):  # Проверяем формат данных
            visits = metrics_data[0] if len(metrics_data) > 0 else 0  # Извлекаем метрики
            pageviews = metrics_data[1] if len(metrics_data) > 1 else 0
            users = metrics_data[2] if len(metrics_data) > 2 else 0
            new_users = metrics_data[3] if len(metrics_data) > 3 else 0
            bounce_rate = metrics_data[4] if len(metrics_data) > 4 else 0
            avg_duration = metrics_data[5] if len(metrics_data) > 5 else 0
            
            response_text = (
                f"📊 Статистика за промежуток: Вчера - Сегодня\n\n"
                f"👁 Посещения: {int(visits)}\n"
                f"📄 Просмотры страниц: {int(pageviews)}\n"
                f"👤 Пользователи: {int(users)}\n"
                f"🆕 Новые пользователи: {int(new_users)}\n"
                f"📉 Процент отказов: {bounce_rate:.2f}%\n"
                f"⏱️ Средняя длительность визита: {int(avg_duration // 60)} мин {int(avg_duration % 60)} сек\n\n"
            )
        else:
            response_text = "❌ Неверный формат данных статистики.\n"
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
    
    await message.answer(response_text)  # Отправляем ответ пользователю

async def date27(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)  # Создаём объект API

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:newUsers,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
        "date1": "7daysAgo", # Дата за неделю
        "date2": "today",
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)  # Запрашиваем данные
    print("Raw data from Yandex Metrica:")
    print(data)  # Выводим в консоль полученные данные

    response_text = ""  # Строка ответа

    if data and data['data']:  # Если данные получены
        report_data = data['data'][0]
        
        metrics_data = report_data.get('metrics')  # Достаём метрики
        if metrics_data and isinstance(metrics_data, list):  # Проверяем формат данных
            visits = metrics_data[0] if len(metrics_data) > 0 else 0  # Извлекаем метрики
            pageviews = metrics_data[1] if len(metrics_data) > 1 else 0
            users = metrics_data[2] if len(metrics_data) > 2 else 0
            new_users = metrics_data[3] if len(metrics_data) > 3 else 0
            bounce_rate = metrics_data[4] if len(metrics_data) > 4 else 0
            avg_duration = metrics_data[5] if len(metrics_data) > 5 else 0
            
            response_text = (
                f"📊 Статистика за эту неделю:\n\n"
                f"👁 Посещения: {int(visits)}\n"
                f"📄 Просмотры страниц: {int(pageviews)}\n"
                f"👤 Пользователи: {int(users)}\n"
                f"🆕 Новые пользователи: {int(new_users)}\n"
                f"📉 Процент отказов: {bounce_rate:.2f}%\n"
                f"⏱️ Средняя длительность визита: {int(avg_duration // 60)} мин {int(avg_duration % 60)} сек\n\n"
            )
        else:
            response_text = "❌ Неверный формат данных статистики.\n"
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
    
    await message.answer(response_text)  # Отправляем ответ пользователю

async def date2month(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)  # Создаём объект API

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:newUsers,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
        "date1": start_date, # Дата за месяц
        "date2": end_date,
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)  # Запрашиваем данные
    print("Raw data from Yandex Metrica:")
    print(data)  # Выводим в консоль полученные данные

    response_text = ""  # Строка ответа

    if data and data['data']:  # Если данные получены
        report_data = data['data'][0]
        
        metrics_data = report_data.get('metrics')  # Достаём метрики
        if metrics_data and isinstance(metrics_data, list):  # Проверяем формат данных
            visits = metrics_data[0] if len(metrics_data) > 0 else 0  # Извлекаем метрики
            pageviews = metrics_data[1] if len(metrics_data) > 1 else 0
            users = metrics_data[2] if len(metrics_data) > 2 else 0
            new_users = metrics_data[3] if len(metrics_data) > 3 else 0
            bounce_rate = metrics_data[4] if len(metrics_data) > 4 else 0
            avg_duration = metrics_data[5] if len(metrics_data) > 5 else 0
            
            response_text = (
                f"📊 Статистика за этот месяц:\n\n"
                f"👁 Посещения: {int(visits)}\n"
                f"📄 Просмотры страниц: {int(pageviews)}\n"
                f"👤 Пользователи: {int(users)}\n"
                f"🆕 Новые пользователи: {int(new_users)}\n"
                f"📉 Процент отказов: {bounce_rate:.2f}%\n"
                f"⏱️ Средняя длительность визита: {int(avg_duration // 60)} мин {int(avg_duration % 60)} сек\n\n"
            )
        else:
            response_text = "❌ Неверный формат данных статистики.\n"
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
    
    await message.answer(response_text)  # Отправляем ответ пользователю

async def date2utm1(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits",
        "dimensions": "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign",
        "date1": "1daysAgo", # Дата со вчерашнего дня
        "date2": "today",
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)
    print("Raw data from Yandex Metrica:")
    print(data)

    response_text = ""

    # --- Сводка по UTM меткам ---
    utm_summary_text = " 📊 Сводка по UTM меткам за вчерашний день:\n"
    utm_data_found = False

    if data and data['data']:
        for row in data['data']:
            if 'dimensions' in row and 'metrics' in row:
                dimensions = row['dimensions']
                metrics = row['metrics']

                print("DEBUG: dimensions =", dimensions)  # Отладочный вывод

                utm_source = "N/A"
                utm_medium = "N/A"
                utm_campaign = "N/A"

                if dimensions:  # Проверяем, что dimensions не пустой
                    utm_source = dimensions[0].get('name', 'N/A') if len(dimensions) > 0 else "N/A"
                    utm_medium = dimensions[1].get('name', 'N/A') if len(dimensions) > 1 else "N/A"
                    utm_campaign = dimensions[2].get('name', 'N/A') if len(dimensions) > 2 else "N/A"

                visits_utm = metrics[0] if metrics else 0
                utm_summary_text += f"- 🔗 Источник: {utm_source}, 📡 Канал: {utm_medium}, 🎯 Кампания: {utm_campaign} - 👁 Посещения: {int(visits_utm)}\n"
                utm_data_found = True

        if utm_data_found:
            response_text += utm_summary_text
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
        print("Ошибка: Не удалось получить данные из data['data']")

    await message.answer(response_text)

async def date2utm7(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits",
        "dimensions": "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign",
        "date1": "7daysAgo", # Дата за неделю
        "date2": "today",
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)
    print("Raw data from Yandex Metrica:")
    print(data)

    response_text = ""

    # --- Сводка по UTM меткам ---
    utm_summary_text = " 📊 Сводка по UTM меткам за неделю:\n"
    utm_data_found = False

    if data and data['data']:
        for row in data['data']:
            if 'dimensions' in row and 'metrics' in row:
                dimensions = row['dimensions']
                metrics = row['metrics']

                print("DEBUG: dimensions =", dimensions)  # Отладочный вывод

                utm_source = "N/A"
                utm_medium = "N/A"
                utm_campaign = "N/A"

                if dimensions:  # Проверяем, что dimensions не пустой
                    utm_source = dimensions[0].get('name', 'N/A') if len(dimensions) > 0 else "N/A"
                    utm_medium = dimensions[1].get('name', 'N/A') if len(dimensions) > 1 else "N/A"
                    utm_campaign = dimensions[2].get('name', 'N/A') if len(dimensions) > 2 else "N/A"

                visits_utm = metrics[0] if metrics else 0
                utm_summary_text += f"- 🔗 Источник: {utm_source}, 📡 Канал: {utm_medium}, 🎯 Кампания: {utm_campaign} - 👁 Посещения: {int(visits_utm)}\n"
                utm_data_found = True

        if utm_data_found:
            response_text += utm_summary_text
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
        print("Ошибка: Не удалось получить данные из data['data']")

    await message.answer(response_text)

async def date2utmmonth(message: types.Message):
    metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)

    params = {
        "ids": COUNTER_ID,
        "metrics": "ym:s:visits",
        "dimensions": "ym:s:UTMSource,ym:s:UTMMedium,ym:s:UTMCampaign",
        "date1": start_date, # Дата за последний месяц
        "date2": end_date,
        "accuracy": "full"
    }

    data = metrika.get_data(COUNTER_ID, params)
    print("Raw data from Yandex Metrica:")
    print(data)

    response_text = ""

    # --- Сводка по UTM меткам ---
    utm_summary_text = " 📊 Сводка по UTM меткам за месяц:\n"
    utm_data_found = False

    if data and data['data']:
        for row in data['data']:
            if 'dimensions' in row and 'metrics' in row:
                dimensions = row['dimensions']
                metrics = row['metrics']

                print("DEBUG: dimensions =", dimensions)  # Отладочный вывод

                utm_source = "N/A"
                utm_medium = "N/A"
                utm_campaign = "N/A"

                if dimensions:  # Проверяем, что dimensions не пустой
                    utm_source = dimensions[0].get('name', 'N/A') if len(dimensions) > 0 else "N/A"
                    utm_medium = dimensions[1].get('name', 'N/A') if len(dimensions) > 1 else "N/A"
                    utm_campaign = dimensions[2].get('name', 'N/A') if len(dimensions) > 2 else "N/A"

                visits_utm = metrics[0] if metrics else 0
                utm_summary_text += f"- 🔗 Источник: {utm_source}, 📡 Канал: {utm_medium}, 🎯 Кампания: {utm_campaign} - 👁 Посещения: {int(visits_utm)}\n"
                utm_data_found = True

        if utm_data_found:
            response_text += utm_summary_text
    else:
        response_text = "❌ Не удалось получить данные статистики.\n"
        print("Ошибка: Не удалось получить данные из data['data']")

    await message.answer(response_text)

@router.callback_query() # обработка колбеков
async def process_callback(callback_query: CallbackQuery, state: FSMContext): 
    data = callback_query.data
    global choicestat # Объявляем переменную как глобальную

    if data == "checkstat":
        choicestat = "standart" # Изменяем значение переменной на стандарт, чтобы получать статистику без UTM меток
        await callback_query.bot.edit_message_text(
            text="☑️ Выберите временной промежуток, за который хотите получить статистику",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=choice
        )

    if data == "checkstatutm":
        choicestat = "utm" # Изменяем значение переменной на UTM, чтобы получать статистику с UTM метками
        await callback_query.bot.edit_message_text(
            text="☑️ Выберите временной промежуток, за который хотите получить статистику",
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            reply_markup=choice
        )

    if data == "yesterday":
        if choicestat == "standart": # Проверяем, равна ли переменная значению стандарт
            await date21(callback_query.message) # Выводим статистику без UTM меток со вчерашнего дня
        else: # Иначе, если не равна стандарту
            await date2utm1(callback_query.message) # Выводим статистику с UTM метками со вчерашнего дня

    if data == "week":
        if choicestat == "standart":
            await date27(callback_query.message)
        else:
            await date2utm7(callback_query.message)

    if data == "month":
        if choicestat == "standart":
            await date2month(callback_query.message)
        else:
            await date2utmmonth(callback_query.message)

    if data == "otherdate":
        if choicestat == "standart":
            await state.set_state(Form.date1) # Присваиваем состояние date1
        else:
            await state.set_state(Form.date1utm) # Присваиваем состояние date1utm
        await callback_query.message.answer("✍️ Отправьте дату с какого числа, месяца и год нужна статистика (пример: 2025-02-01)")

async def main():
    dp.include_router(router) # инициализация роутера
    await dp.start_polling(bot) # запуск бота

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) # инициализация логгера
    try:
        asyncio.run(main()) # запускаем функцию main в асинхронном режиме
    except KeyboardInterrupt:
        print('Бот выключен')