from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import get_events, add_event, update_event, delete_event, update_payment_link, add_payment_link
from keyboards.main_menu import get_main_menu
from datetime import datetime
from io import BytesIO
import pandas as pd
import sqlite3
from aiogram.types import FSInputFile


router = Router()

choice_name = {
    "name": "Название",
    "description": "Описание",
    "photo": "Фото",
    "price": "Цена",
    "date": "Дата (Используйте формат ГГГГ-ММ-ДД ЧЧ:ММ)",
    "is_sale_active": "Статус продаж",
    "qr_template": "QR-шаблон",
    "photo_album_link": "Фотоальбом (или слово 'Нет')"
}

def validate_date_format(date_str: str, date_format: str = "%Y-%m-%d %H:%M") -> bool:
    try:
        datetime.strptime(date_str, date_format)
        return True
    except ValueError:
        return False

# Состояния для управления мероприятиями
class EventManagementStates(StatesGroup):
    waiting_for_event_name = State()
    waiting_for_event_description = State()
    waiting_for_event_photo = State()
    waiting_for_event_price = State()
    waiting_for_event_date = State()
    waiting_for_event_is_sale_active = State()
    waiting_for_event_qr_template = State()
    waiting_for_event_photo_album_link = State()
    waiting_for_event_edit_choice = State()
    waiting_for_new_value = State()
    waiting_for_new_value_qr = State()
    waiting_for_new_value_sale = State()
    waiting_for_event_delete_choice = State()
    waiting_payment_link = State()


def export_event_attendees_to_excel(event_id: int, output_file: str = "Список гостей.xlsx"):
    # Подключаемся к базе данных
    conn = sqlite3.connect("rout_bot.db")
    cursor = conn.cursor()

    # Запрос для получения данных о пользователях, купивших билеты на мероприятие
    query = """
        SELECT u.full_name, u.university, u.phone_number
        FROM users u
        JOIN tickets t ON u.id = t.user_id
        WHERE t.event_id = ?
    """
    cursor.execute(query, (event_id,))
    attendees = cursor.fetchall()

    # Закрываем соединение с базой данных
    conn.close()

    # Если данные найдены, создаём DataFrame и сохраняем в Excel
    if attendees:
        # Создаём DataFrame из данных
        df = pd.DataFrame(attendees, columns=["ФИО", "Университет", "Номер телефона"])

        # Сохраняем DataFrame в Excel-файл
        df.to_excel(output_file, index=False)
        print(f"Данные успешно экспортированы в файл {output_file}")
    else:
        print("На данное мероприятие билеты не куплены.")


@router.message(F.text == "📄 Получить список гостей")
async def get_guests(message: types.Message, state: FSMContext):
    events = get_events()
    if not events:
        await message.answer("Нет доступных мероприятий.")
        return

    # Создаем inline-клавиатуру с мероприятиями
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.button(text=event["name"], callback_data=f"guests_event_{event['id']}")
    builder.adjust(1)  # По одной кнопке в строке

    await message.answer("Выберите мероприятие для редактирования:", reply_markup=builder.as_markup())


# Обработка выбора мероприятия для редактирования
@router.callback_query(F.data.startswith("guests_event_"))
async def get_guests_event(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[-1])
    await callback.message.delete()

    export_event_attendees_to_excel(event_id)

    await callback.message.answer_document(
        document=FSInputFile("Список гостей.xlsx")
    )
    await callback.answer()



# Обработка кнопки "💰 Обновить ссылку для оплаты"
@router.message(F.text == "💰 Обновить ссылку для оплаты")
async def manage_payment_link(message: types.Message, state: FSMContext):
    await message.answer("Введите новую ссылку для оплаты")
    await state.set_state(EventManagementStates.waiting_payment_link)


@router.message(EventManagementStates.waiting_payment_link)
async def update_payment_link_f(message: types.Message, state: FSMContext):
    update_payment_link(message.text)
    await message.answer("Ссылка успешно обновлена!")
    await state.clear()


# Обработка кнопки "⚙️ Управление мероприятиями"
@router.message(F.text == "⚙️ Управление мероприятиями")
async def manage_events(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить мероприятие", callback_data="add_event")
    builder.button(text="Редактировать мероприятие", callback_data="edit_event")
    builder.button(text="Удалить мероприятие", callback_data="delete_event")
    builder.adjust(1)  # По одной кнопке в строке

    await message.answer("Выберите действие:", reply_markup=builder.as_markup())

# Обработка добавления мероприятия
@router.callback_query(F.data == "add_event")
async def add_event_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите название мероприятия:")
    await state.set_state(EventManagementStates.waiting_for_event_name)
    await callback.answer()

@router.message(EventManagementStates.waiting_for_event_name)
async def process_event_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите описание мероприятия:")
    await state.set_state(EventManagementStates.waiting_for_event_description)

@router.message(EventManagementStates.waiting_for_event_description)
async def process_event_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Отправьте фото мероприятия:")
    await state.set_state(EventManagementStates.waiting_for_event_photo)

@router.message(EventManagementStates.waiting_for_event_photo, F.photo)
async def process_event_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Введите цену билета:")
    await state.set_state(EventManagementStates.waiting_for_event_price)

@router.message(EventManagementStates.waiting_for_event_price)
async def process_event_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите дату мероприятия (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
        await state.set_state(EventManagementStates.waiting_for_event_date)
    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте еще раз.")

@router.message(EventManagementStates.waiting_for_event_date)
async def process_event_date(message: types.Message, state: FSMContext):
    date_str = message.text
    if not validate_date_format(date_str):
        await message.answer("Неверный формат даты. Используйте формат ГГГГ-ММ-ДД ЧЧ:ММ.")
        return

    await state.update_data(date=date_str)
    await message.answer("Продажа билетов активна? (Да/Нет):")
    await state.set_state(EventManagementStates.waiting_for_event_is_sale_active)

@router.message(EventManagementStates.waiting_for_event_is_sale_active)
async def process_event_sale_status(message: types.Message, state: FSMContext):
    is_sale_active = message.text.lower() in ["да", "yes", "true"]
    await state.update_data(is_sale_active=is_sale_active)
    await message.answer("Отправьте шаблон для QR-кода (фото):")
    await state.set_state(EventManagementStates.waiting_for_event_qr_template)

@router.message(EventManagementStates.waiting_for_event_qr_template, F.photo)
async def process_event_qr_template(message: types.Message, state: FSMContext):
    qr_template_file_id  = message.photo[-1].file_id

    # Загружаем файл в память
    file = await message.bot.get_file(qr_template_file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    # Сохраняем файл на диск
    qr_template_path = f"qr_templates/template_{message.from_user.id}.png"
    with open(qr_template_path, "wb") as f:
        f.write(file_bytes.getvalue())

    await state.update_data(qr_template=qr_template_path)
    await message.answer("Введите ссылку на фотоальбом (или слово 'Нет'):")
    await state.set_state(EventManagementStates.waiting_for_event_photo_album_link)

@router.message(EventManagementStates.waiting_for_event_photo_album_link)
async def process_event_photo_album_link(message: types.Message, state: FSMContext):
    photo_album_link = message.text if message.text else None
    await state.update_data(photo_album_link=photo_album_link)

    # Сохраняем мероприятие в базу данных
    event_data = await state.get_data()
    print(event_data)
    add_event(**event_data)

    await message.answer("Мероприятие успешно добавлено!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

# Обработка кнопки "Редактировать мероприятие"
@router.callback_query(F.data == "edit_event")
async def edit_event_start(callback: types.CallbackQuery, state: FSMContext):
    events = get_events()
    if not events:
        await callback.message.answer("Нет доступных мероприятий для редактирования.")
        await callback.answer()
        return

    # Создаем inline-клавиатуру с мероприятиями
    builder = InlineKeyboardBuilder()
    for event in events:
        builder.button(text=event["name"], callback_data=f"edit_event_{event['id']}")
    builder.adjust(1)  # По одной кнопке в строке
    await callback.message.delete()

    await callback.message.answer("Выберите мероприятие для редактирования:", reply_markup=builder.as_markup())
    await callback.answer()

# Обработка выбора мероприятия для редактирования
@router.callback_query(F.data.startswith("edit_event_"))
async def choose_event_to_edit(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[-1])
    await state.update_data(event_id=event_id)

    # Создаем inline-клавиатуру с параметрами для редактирования
    builder = InlineKeyboardBuilder()
    builder.button(text="Название", callback_data="edit_name")
    builder.button(text="Описание", callback_data="edit_description")
    builder.button(text="Фото", callback_data="edit_photo")
    builder.button(text="Цена", callback_data="edit_price")
    builder.button(text="Дата", callback_data="edit_date")
    builder.button(text="Статус продаж", callback_data="edit_is_sale_active")
    builder.button(text="QR-шаблон", callback_data="edit_qr_template")
    builder.button(text="Фотоальбом", callback_data="edit_photo_album_link")
    builder.adjust(2)  # По две кнопки в строке
    await callback.message.delete()

    await callback.message.answer("Что вы хотите изменить?", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "edit_is_sale_active")
async def choose_sale_status_to_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Продажа билетов активна? (Да/Нет):")
    await state.set_state(EventManagementStates.waiting_for_new_value_sale)
    await callback.answer()

@router.message(EventManagementStates.waiting_for_new_value_sale)
async def process_new_sale_status(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    # Проверяем, есть ли в состоянии event_id
    if "event_id" not in user_data:
        await message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    event_id = user_data["event_id"]
    user_input = message.text.lower()

    # Преобразуем ответ пользователя в булево значение
    if user_input in ["да", "yes", "true", "1"]:
        new_sale_status = True
    elif user_input in ["нет", "no", "false", "0"]:
        new_sale_status = False
    else:
        await message.answer("Неверный ответ. Пожалуйста, введите 'Да' или 'Нет'.")
        return

    # Обновляем статус продаж в базе данных
    update_event(event_id, is_sale_active=new_sale_status)

    await message.answer(f"Статус продаж успешно обновлен на {'активен' if new_sale_status else 'неактивен'}!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

@router.callback_query(F.data == "edit_qr_template")
async def choose_qr_to_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новое фото для шаблона QR-кода:")
    await state.set_state(EventManagementStates.waiting_for_new_value_qr)
    await callback.answer()

@router.message(EventManagementStates.waiting_for_new_value_qr, F.photo)
async def process_new_qr(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    # Проверяем, есть ли в состоянии event_id
    if "event_id" not in user_data:
        await message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    event_id = user_data["event_id"]

    # Загружаем новое фото шаблона QR-кода
    try:
        file = await message.bot.get_file(message.photo[-1].file_id)
        file_bytes = await message.bot.download_file(file.file_path)

        # Сохраняем файл на диск
        qr_template_path = f"qr_templates/template_{event_id}.png"
        with open(qr_template_path, "wb") as f:
            f.write(file_bytes.getvalue())

        # Обновляем шаблон QR-кода мероприятия в базе данных
        update_event(event_id, qr_template=qr_template_path)

        await message.answer("Шаблон QR-кода успешно обновлен!", reply_markup=get_main_menu(message.from_user.id))
    except Exception as e:
        await message.answer(f"Ошибка при обновлении шаблона QR-кода: {e}")
    finally:
        await state.clear()

@router.callback_query(F.data == "edit_photo")
async def choose_photo_to_edit(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте новое фото для мероприятия:")
    await state.set_state(EventManagementStates.waiting_for_new_value)
    await callback.answer()

@router.message(EventManagementStates.waiting_for_new_value, F.photo)
async def process_new_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    # Проверяем, есть ли в состоянии event_id
    if "event_id" not in user_data:
        await message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    event_id = user_data["event_id"]
    new_photo = message.photo[-1].file_id  # Получаем file_id новой фотографии

    # Обновляем фото мероприятия в базе данных
    update_event(event_id, photo=new_photo)

    await message.answer("Фото мероприятия успешно обновлено!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

# Обработка выбора параметра для редактирования
@router.callback_query(F.data.startswith("edit_"))
async def choose_parameter_to_edit(callback: types.CallbackQuery, state: FSMContext):
    parameter = callback.data  # Например, "edit_name"
    await state.update_data(parameter=parameter)

    await callback.message.delete()

    # Запрашиваем новое значение
    await callback.message.answer(f"Введите новое значение для {choice_name[parameter.replace('edit_', '')]}:")
    await state.set_state(EventManagementStates.waiting_for_new_value)
    await callback.answer()

# Обработка ввода нового значения
@router.message(EventManagementStates.waiting_for_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    # Проверяем, есть ли в состоянии event_id и parameter
    if "event_id" not in user_data or "parameter" not in user_data:
        await message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    event_id = user_data["event_id"]
    parameter = user_data["parameter"]
    new_value = message.text

    # Обновляем мероприятие в базе данных
    update_event(event_id, **{parameter.replace("edit_", ""): new_value})

    await message.answer(f"Параметр '{choice_name[parameter.replace('edit_', '')]}' успешно обновлен!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

# Обработка удаления мероприятия
@router.callback_query(F.data == "delete_event")
async def delete_event_start(callback: types.CallbackQuery):
    events = get_events()
    if not events:
        await callback.message.answer("Нет доступных мероприятий для удаления.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for event in events:
        builder.button(text=event["name"], callback_data=f"delete_event_{event['id']}")
    builder.adjust(1)  # По одной кнопке в строке

    await callback.message.answer("Выберите мероприятие для удаления:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("delete_event_"))
async def delete_event_confirm(callback: types.CallbackQuery):
    event_id = int(callback.data.split("_")[-1])
    delete_event(event_id)
    await callback.message.answer("Мероприятие успешно удалено!", reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()