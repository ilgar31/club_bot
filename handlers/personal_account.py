from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton
from keyboards.main_menu import get_main_menu
from database import get_user, get_user_events, add_user, update_user, get_user_tickets
import time
from aiogram.types import FSInputFile

router = Router()

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_university = State()
    waiting_for_contact = State()

# Обработка команды "Личный кабинет"
@router.message(F.text == "Личный кабинет")
async def personal_account(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        # Если пользователь не зарегистрирован, начинаем процесс регистрации
        await message.answer("Вы не зарегистрированы. Давайте зарегистрируем вас!")
        time.sleep(1)
        await message.answer("Укажите ваше имя и фамилию:", reply_markup=get_cancel_keyboard())
        await state.set_state(RegistrationStates.waiting_for_name)
    else:
        # Если пользователь зарегистрирован, показываем личный кабинет
        await show_personal_account(message, user)

# Обработка ввода имени и фамилии
@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Регистрация отменена.", reply_markup=get_main_menu(message.chat.id))
        return

    await state.update_data(full_name=message.text)  # Сохраняем имя и фамилию
    await message.answer("Укажите ваш вуз и факультет:", reply_markup=get_cancel_keyboard())
    await state.set_state(RegistrationStates.waiting_for_university)

# Обработка ввода вуза и факультета
@router.message(RegistrationStates.waiting_for_university)
async def process_university(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Регистрация отменена.", reply_markup=get_main_menu(message.chat.id))
        return

    await state.update_data(university=message.text)  # Сохраняем вуз и факультет
    await message.answer("Поделитесь вашим контактом, нажав кнопку ниже:", reply_markup=get_contact_keyboard())
    await state.set_state(RegistrationStates.waiting_for_contact)

# Обработка контакта
@router.message(RegistrationStates.waiting_for_contact, F.contact)
async def process_contact(message: types.Message, state: FSMContext):
    contact = message.contact
    user_data = await state.get_data()

    # Сохраняем пользователя в базу данных
    add_user(
        user_id=message.from_user.id,
        full_name=user_data["full_name"],
        university=user_data["university"],
        phone_number=contact.phone_number
    )

    await message.answer("Регистрация завершена! Спасибо.", reply_markup=get_main_menu(message.chat.id))
    await state.clear()  # Очищаем состояние
    time.sleep(1)
    # Показываем личный кабинет
    await show_personal_account(message, get_user(message.from_user.id))

# Обработка отмены на этапе ожидания контакта
@router.message(RegistrationStates.waiting_for_contact)
async def cancel_contact(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Регистрация отменена.", reply_markup=get_main_menu(message.chat.id))

# Функция для показа личного кабинета
async def show_personal_account(message: types.Message, user: dict):
    builder = InlineKeyboardBuilder()
    builder.button(text="Мои тусовки", callback_data="my_events")
    builder.button(text="Мои билеты", callback_data="my_tickets")
    builder.button(text="Редактировать данные", callback_data="edit_data")

    await message.answer(
        f"Имя: {user['full_name']}\n"
        f"Номер телефона: {user['phone_number']}\n"
        f"Вуз: {user['university']}\n"
        f"Количество посещенных тусовок: {len(get_user_events(user['id']))}",
        reply_markup=builder.as_markup()
    )

# Клавиатура для запроса контакта
def get_contact_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Клавиатура для отмены
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# Состояния для редактирования данных
class EditDataStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_university = State()

# Обработка кнопки "Мои тусовки"
@router.callback_query(F.data == "my_events")
async def my_events(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Вы не зарегистрированы.", reply_markup=get_main_menu(callback.message.chat.id))
        return

    user_events = get_user_events(user["id"])
    if not user_events:
        await callback.message.answer("Вы еще не посещали мероприятия.")
        await callback.answer()
        return

    # Формируем сообщение с посещенными мероприятиями
    events_text = "Ваши тусовки:\n\n"
    for event in user_events:
        events_text += f"🎉 {event['name']}\n"
        if event.get("photo_album_link") != 'Нет':
            events_text += f"📸 [Фотоальбом]({event['photo_album_link']})\n"
        events_text += "\n"

    await callback.message.answer(events_text, parse_mode="Markdown")
    await callback.answer()

# Обработка кнопки "Мои билеты"
@router.callback_query(F.data == "my_tickets")
async def my_tickets(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.answer("Вы не зарегистрированы.", reply_markup=get_main_menu(callback.message.chat.id))
        return

    # Получаем билеты пользователя
    user_tickets = get_user_tickets(user["id"])
    if not user_tickets:
        await callback.message.answer("У вас нет купленных билетов.")
        await callback.answer()
        return

    # Отправляем билеты пользователю
    for ticket in user_tickets:
        photo = FSInputFile(ticket["qr_code"])
        await callback.message.answer_photo(
            photo=photo,
            caption=f"Билет на мероприятие: {ticket['event_name']}"
        )

    await callback.answer()

# Обработка кнопки "Редактировать данные"
@router.callback_query(F.data == "edit_data")
async def edit_data(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Укажите ваше новое имя и фамилию:", reply_markup=get_cancel_keyboard())
    await state.set_state(EditDataStates.waiting_for_name)
    await callback.answer()

# Обработка ввода нового имени
@router.message(EditDataStates.waiting_for_name)
async def process_new_name(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_menu(message.chat.id))
        return

    await state.update_data(full_name=message.text)
    await message.answer("Укажите ваш новый вуз и факультет:", reply_markup=get_cancel_keyboard())
    await state.set_state(EditDataStates.waiting_for_university)

# Обработка ввода нового вуза
@router.message(EditDataStates.waiting_for_university)
async def process_new_university(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("Редактирование отменено.", reply_markup=get_main_menu(message.chat.id))
        return

    user_data = await state.get_data()
    update_user(
        user_id=message.from_user.id,
        full_name=user_data["full_name"],
        university=message.text
    )

    await message.answer("Данные успешно обновлены!", reply_markup=get_main_menu(message.chat.id))
    await state.clear()