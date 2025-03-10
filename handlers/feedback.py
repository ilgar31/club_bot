from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.main_menu import get_main_menu
from database import get_user_events, add_feedback, get_event_by_id, get_user # Импортируем функцию для получения мероприятий пользователя
from config import ADMINS

router = Router()

# Состояния для оставления отзыва
class FeedbackStates(StatesGroup):
    waiting_for_event = State()
    waiting_for_feedback = State()
    
@router.message(F.text == "Обратная связь")
async def feedback(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Связаться с менеджером", callback_data="contact_manager")
    builder.button(text="Оставить отзыв", callback_data="leave_feedback")

    await message.answer("Выберите действие:", reply_markup=builder.as_markup())

# Обработка кнопки "Связаться с менеджером"
@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: types.CallbackQuery):
    await callback.message.answer("Свяжитесь с менеджером: @admin_username")
    await callback.answer()

# Обработка кнопки "Оставить отзыв"
@router.callback_query(F.data == "leave_feedback")
async def leave_feedback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_events = get_user_events(user_id)  # Получаем мероприятия пользователя

    if not user_events:
        await callback.message.answer("Вы еще не посещали мероприятия.")
        await callback.answer()
        return

    # Создаем inline-клавиатуру с мероприятиями пользователя
    builder = InlineKeyboardBuilder()
    for event in user_events:
        builder.button(text=event["name"], callback_data=f"feedback_event_{event['id']}")
    builder.adjust(1)  # По одной кнопке в строке

    await callback.message.answer("На какое мероприятие вы хотите оставить отзыв?", reply_markup=builder.as_markup())
    await callback.answer()

# Обработка выбора мероприятия для отзыва
@router.callback_query(F.data.startswith("feedback_event_"))
async def choose_event_for_feedback(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[-1])  # Извлекаем ID мероприятия
    await state.update_data(event_id=event_id)  # Сохраняем ID мероприятия в состоянии
    await callback.message.answer("Оставьте свой отзыв:")
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback.answer()

# Обработка текста отзыва
@router.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    feedback_text = message.text
    user_data = await state.get_data()
    event_id = user_data["event_id"]

    # Сохраняем отзыв в базу данных (функция add_feedback должна быть реализована в database.py)
    add_feedback(message.from_user.id, event_id, feedback_text)

    event = get_event_by_id(event_id)
    user = get_user(message.from_user.id)

    await message.answer("Спасибо за ваш отзыв! Он был отправлен администраторам.")
    for admin_id in ADMINS:
        await message.bot.send_message(admin_id, f"Пользователь оставил отзыв о мероприятии: {event['name']}.\n\n👤 Имя: {user['full_name']}\n☎️ Контакт: {user['phone_number']}\n📱 Telegram: @{message.from_user.username}\nОтзыв: {feedback_text}")
    await state.clear()  # Очищаем состояние