from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from config import ADMINS

def get_main_menu(user_id):

    buttons = [
        [KeyboardButton(text="Купить билет")],
        [KeyboardButton(text="Личный кабинет")],
        [KeyboardButton(text="Обратная связь")]
    ]


    # Если пользователь админ, добавляем кнопку управления акциями
    if user_id in ADMINS:
        buttons.append([KeyboardButton(text="⚙️ Управление мероприятиями")])
        buttons.append([KeyboardButton(text="💰 Обновить ссылку для оплаты")])

    # Создаем клавиатуру с кнопками
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    return keyboard
