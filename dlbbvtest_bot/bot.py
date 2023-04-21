import logging
import requests

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, filters
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import Poll, PollType, ReplyKeyboardMarkup, KeyboardButton

# Импорт модулей из проекта
from config import API_TOKEN, API_CONVERT_TOKEN
import get_weather
from checkValue import *


# Отдельно от словаря, чтобы не дублировать
CANCEL = "\n/cancel - отменить выполнение команды"

# Словарь для всех фраз, которые говорит бот + api ссылки
TEXT_MESSAGES_DICT = {
    'help': f"""
Я знаю следующие команды:
/help - узнать список команд
/start - начать работу
/weather - узнать погоду в указанном городе
/convert - конвертировать валюту
/pet - получить фотографию милого котика
/poll - создать опрос
{CANCEL}
""",
    'start': 'Привет, {}!\nНапиши любую из доступных команд \nЧтобы узнать, что я умею - напиши /help',
    'getcity': f'Введите название города без сокращений:\n{CANCEL}',
    'api_url_pet': 'https://api.thecatapi.com/v1/images/search',
    'pet_server_error': 'Не удалось получить фото кота',
    'cancel': 'Что отменять то?',
    'canceled': 'Команда отменена.',
    'convert_api': 'https://openexchangerates.org/api/latest.json?app_id={}&base={}&symbols={}&amount=100',
    'getval_currency_from': f'Введите код валюты, которую вы хотели бы конвертировать:\n{CANCEL}',
    'getval_currency_to': f'Введите код валюты, в которую вы хотели бы конвертировать:\n{CANCEL}',
    'val_error': 'Вы неверно ввели код валюты. Начните заново /convert',
    'getval_server_error': 'Не удалось подключиться к серверу для конвертации валют.\nВозможно, это делают слишком часто',
    'pool_question': f'Введите вопрос для опроса:\n{CANCEL}',
    'pool_answer': f'Вводите варианты ответа, каждый - новым сообщением.\nЧтобы закончить ввод, нажмите кнопку "Готово"\n{CANCEL}',
    'pool_answer_added': 'Добавлен вариант ответа: {}\nВведите следующий вариант либо нажмите кнопку "Готово"\n{}',
    'pool_end': 'Готово',
    'unknow_command': 'Я не знаю такой команды\nУзнать список доступных команд - /help',
    'bot_is_on': 'Бот запущен'
}


# Для города при получении погоды
class Form(StatesGroup):
    name = State()


# Для валют при конвертации
class Conversation(StatesGroup):
    currency_from = State()
    currency_to = State()


# Для вопроса и ответов при создании опроса
class PollCreation(StatesGroup):
    question = State()
    options = State()


# Логирование 
logging.basicConfig(level=logging.INFO)


# Создание объекта бота 
storage = MemoryStorage() # Для функционирования FSM
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)


# Обработка команды /help 
@dp.message_handler(commands=['help'])
async def message_help(message: types.Message):
    await message.answer(TEXT_MESSAGES_DICT['help'])


# Обработка команды /start 
@dp.message_handler(commands=['start'])
async def message_start(message: types.Message):
    user_name = message.from_user.full_name
    await message.reply(TEXT_MESSAGES_DICT['start'].format(user_name))


# Обработка команды /cancel для отмены работы в процессе работы с другой командой
@dp.message_handler(state='*', commands=['cancel']) # state='*', чтобы работало везде
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(TEXT_MESSAGES_DICT['cancel'])
        return # Выходим из команды
    
    await state.finish()
    await message.reply(TEXT_MESSAGES_DICT['canceled'], reply_markup=types.ReplyKeyboardRemove())


# Обработка команды /weather 
@dp.message_handler(commands=['weather'])
async def message_weater(message: types.Message):
    await message.answer(TEXT_MESSAGES_DICT['getcity'])
    await Form.name.set()

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.finish()
    await message.reply(get_weather.get_weather(message.text)) # Передаем название города в функцию определения погоды


# Обработка команды /pet
@dp.message_handler(commands=['pet'])
async def message_weater(message: types.Message):
    response = requests.get(TEXT_MESSAGES_DICT['api_url_pet'])
    if response.ok:
        photo_url = response.json()[0]['url']
        await bot.send_photo(message.chat.id, photo_url)
    else:
        await message.answer(TEXT_MESSAGES_DICT['pet_server_error'])


# Начало обработки команды /convert
@dp.message_handler(commands=['convert'])
async def cmd_convert_start(message: types.Message):
    await message.reply(TEXT_MESSAGES_DICT['getval_currency_from'])
    await Conversation.currency_from.set()

@dp.message_handler(state=Conversation.currency_from)
async def process_currency_from(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['currency_from'] = message.text.upper()
        if checkValue(data['currency_from']): # Проверяем есть ли такой код валюты в нашем api
            await message.answer(TEXT_MESSAGES_DICT['val_error'])
            await state.finish()
            return # Выходим из команды

    await message.reply(TEXT_MESSAGES_DICT['getval_currency_to'])
    await Conversation.currency_to.set()

@dp.message_handler(state=Conversation.currency_to)
async def process_currency_to(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['currency_to'] = message.text.upper()
        if checkValue(data['currency_to']): # Проверяем есть ли такой код валюты в нашем API
            await message.answer(TEXT_MESSAGES_DICT['val_error'])
            await state.finish()
            return
        currency_from = data['currency_from'] # Пишем в переменную валюту, которую конвертируем
        currency_to = data['currency_to'] # Пишем в переменную валюту, в которую конвертируем

    # Формируем URL API для получения текущего курса валют
    api_url = TEXT_MESSAGES_DICT['convert_api'].format(API_CONVERT_TOKEN, currency_from, currency_to)

    try:
    # Получаем текущий курс валют от API
        response = requests.get(api_url)
        response.raise_for_status()  # Вызываем исключение, если статус ответа не равен 200
        data = response.json()
    except requests.exceptions.HTTPError as error:
        await message.answer(TEXT_MESSAGES_DICT['getval_server_error'])
        await state.finish()
    else:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        exchange_rate = data['rates'][currency_to] # Пишем в переменную значение конвертации, аргументы зависят от API

        # Отправляем результат пользователю
        text = f"1 {currency_from} = {exchange_rate} {currency_to}" # Формируем ответ бота в переменную
        await bot.send_message(message.chat.id, text, parse_mode=types.ParseMode.MARKDOWN)

        # Сбрасываем state
        await state.finish()


# Начало обработки команды /pools
@dp.message_handler(commands=['poll'])
async def polls_handler(message: types.Message):
    await message.answer(TEXT_MESSAGES_DICT['pool_question'])
    await PollCreation.question.set()


@dp.message_handler(state=PollCreation.question)
async def get_question(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['question'] = message.text # Сохраняем вопрос
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(KeyboardButton(TEXT_MESSAGES_DICT['pool_end']))
    await message.answer(TEXT_MESSAGES_DICT['pool_answer'], reply_markup=markup)
    await PollCreation.options.set()


@dp.message_handler(filters.Regexp(rf"^(?!{TEXT_MESSAGES_DICT['pool_end']}).*$"), state=PollCreation.options)
async def get_option(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'options' in data:
            data['options'].append(message.text) # Добавляем ответ в список с ответами, если он есть
        else:
            data['options'] = [message.text] # Добавляем ответ, создавая список

    # Объявляем кнопку
    markup = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(KeyboardButton(TEXT_MESSAGES_DICT['pool_end']))

    await message.answer(TEXT_MESSAGES_DICT['pool_answer_added'].format(message.text, CANCEL), reply_markup=markup)


#Создать опрос
@dp.message_handler(filters.Regexp(rf"^{TEXT_MESSAGES_DICT['pool_end']}$"), state=PollCreation.options)
async def create_poll(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        question = data['question'] # Передаем вопрос в переменную, чтобы передать ее в poll
        options = data['options'] # Передаем ответы в переменную, чтобы передать ее в poll

    # Создаем опрос poll
    poll = Poll(
        type=PollType.REGULAR,  # регулярный опрос (не викторина)
        question=data['question'],  # Вопрос опроса
        options=data['options'],  # Варианты ответов
        is_anonymous=False,  # Ответы пользователей не будут анонимными
    )

    # Возвращаем опрос ответом бота
    await message.answer_poll(question=poll.question, options=poll.options, is_anonymous=poll.is_anonymous, reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


# Обработка несуществующих команд
@dp.message_handler()
async def message_err(message: types.Message):
    await message.answer(TEXT_MESSAGES_DICT['unknow_command'])


# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=print(TEXT_MESSAGES_DICT['bot_is_on']))