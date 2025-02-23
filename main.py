import logging
import asyncio
import os
import string
import requests

from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
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

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["TOKEN"]

bot = Bot(token=BOT_TOKEN) # токен, который будет в качестве переменной на хостинге
dp = Dispatcher() # переменная диспетчера
router = Router() # переменная роутера
YANDEX_METRIKA_TOKEN = 'y0__xCqiIblBxiluzUgzPXSrBImnXWxjnlSv8r8kX6xHGJJeR6sjg'
COUNTER_ID = '100012253'

class YandexMetrica:
    def __init__(self, token):  # Исправлено на __init__
        self.token = token
        self.base_url = "https://api-metrika.yandex.net/stat/v1/data"

    def get_data(self, counter_id, params):
        headers = {
            "Authorization": f"OAuth {self.token}"
        }
        params['ids'] = counter_id
        response = requests.get(self.base_url, headers=headers, params=params)
        print(response)

        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f"Error: {response.status_code}, {response.text}")
            if response.status_code == 403:
                logging.error("Access Denied: Проверьте токен и права доступа к счетчику.")
            return None

def is_date(text):
    allowed_chars = string.digits + "-"
    for char in text:
        if char not in allowed_chars:
            return False
    return True

@router.message(CommandStart())
async def start_command(message: types.Message):
    await message.answer("🤖 Это бот для работы с Яндекс Метрикой. Нажми на подходящую кнопку для запроса статистики.", reply_markup=choicestart)

@router.message(Form.date1)
async def date1(message: types.Message, state: FSMContext):
    if is_date(message.text):
        await state.update_data(date1=message.text)
        await state.set_state(Form.date2)
        await message.answer("✍️ Отправьте дату по какое число, месяц и год нужна статистика (пример: 2025-02-28)")
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")

@router.message(Form.date1utm)
async def date1utm(message: types.Message, state: FSMContext):
    if is_date(message.text):
        await state.update_data(date1utm=message.text)
        await state.set_state(Form.date2utm)
        await message.answer("✍️ Отправьте дату по какое число, месяц и год нужна статистика (пример: 2025-02-28)")
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")

@router.message(Form.date2)
async def date2(message: types.Message, state: FSMContext):
    dataaa = await state.get_data()
    if is_date(message.text):
        metrika = YandexMetrica(YANDEX_METRIKA_TOKEN)

        params = {
            "ids": COUNTER_ID,
            "metrics": "ym:s:visits,ym:s:pageviews,ym:s:users,ym:s:newUsers,ym:s:bounceRate,ym:s:avgVisitDurationSeconds",
            "date1": dataaa.get('date1'),
            "date2": message.text,
            "accuracy": "full"
        }

        data = metrika.get_data(COUNTER_ID, params)
        print("Raw data from Yandex Metrica:")
        print(data)

        response_text = ""

        if data and data['data']:
            report_data = data['data'][0]

            metrics_data = report_data.get('metrics')
            if metrics_data and isinstance(metrics_data, list):
                visits = metrics_data[0] if len(metrics_data) > 0 else 0
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
                print("Ошибка: Неверный формат metrics_data:", metrics_data)
        else:
            response_text = "❌ Не удалось получить данные статистики.\n"
            print("Ошибка: Не удалось получить данные из data['data']")

        await message.answer(response_text)
        await state.clear()
    else:
        await message.answer("❌ Отправьте сообщение в формате даты (пример: 2025-11-11)")

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

@router.callback_query() # обработка колбеков
async def process_callback(callback_query: CallbackQuery, state: FSMContext): 
    data = callback_query.data

    if data == "checkstat":
        await state.set_state(Form.date1)
        await callback_query.message.answer("✍️ Отправьте дату с какого числа, месяца и год нужна статистика (пример: 2025-02-01)")

    if data == "checkstatutm":
        await state.set_state(Form.date1utm)
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