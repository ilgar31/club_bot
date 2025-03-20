from aiogram import F, types, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from keyboards.main_menu import get_main_menu
from database import get_ticket, add_ticket, get_payment_link, add_user_event, get_user, get_active_events, get_event_by_id, add_admin_notification, get_admin_notifications, delete_admin_notifications
from config import ADMINS
from aiogram.types import ContentType
import qrcode
from io import BytesIO
from aiogram import types
from aiogram.types import InputFile
import time
import segno
from PIL import Image
import os
from aiogram.types import FSInputFile

async def generate_and_send_ticket(user_id: int, event_id: int, callback: types.CallbackQuery):
    event = get_event_by_id(event_id)
    if not event:
        await callback.message.answer("Ошибка: мероприятие не найдено.")
        return

    # Проверяем, есть ли шаблон QR-кода
    if not event.get("qr_template"):
        await callback.message.answer("Ошибка: шаблон QR-кода не найден.")
        return

    ticket_filename = f"qr_code/ticket_{user_id}_{event_id}.png"
    # Сохраняем билет в базу данных
    add_ticket(user_id, event_id, ticket_filename)
    ticket_id = get_ticket(user_id, event_id)
    bot_username = 'test_bigd_club_bot'
    # Генерация QR-кода
    qrcode = segno.make_qr(f"https://t.me/{bot_username}?start=ticket_{ticket_id}", error='L')
    qrcode.save(
        "qrcode.png",
        scale=5,
        dark="#FFFFFF",  # Белый цвет для QR-кода
        light="#0007BA",  # Фон QR-кода
        border=0  # Уменьшаем размер рамки
    )

    # Открываем QR-код
    qr_image = Image.open("qrcode.png").convert("RGBA")

    # Открываем шаблон QR-кода с диска
    try:
        background = Image.open(event['qr_template']).convert("RGBA")
    except Exception as e:
        await callback.message.answer(f"Ошибка при загрузке шаблона QR-кода: {e}")
        return

    # Координаты выреза для QR-кода
    cutout_box = (259, 559, 479, 779)
    cutout = background.crop(cutout_box)

    # Изменяем размер QR-кода и вставляем его в вырез
    qr_resized = qr_image.resize(cutout.size)
    qr_mask = qr_resized.convert("L").point(lambda x: 255 if x > 0 else 0)
    background.paste(qr_resized, cutout_box, qr_mask)

    # Сохраняем итоговое изображение

    background.save(ticket_filename, format="PNG")

    # Отправляем билет пользователю
    try:
        # Используем путь к файлу для создания InputFile
        photo = FSInputFile(ticket_filename)
        await callback.bot.send_photo(
            chat_id=user_id,
            photo=photo,
            caption=f"Ваш билет на мероприятие: {event['name']}"
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка при отправке билета: {e}")
        return



    # Удаляем временные файлы
    os.remove("qrcode.png")


router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_university = State()
    waiting_for_contact = State()

class PaymentStates(StatesGroup):
    waiting_for_receipt = State()  # Ожидание скриншота квитанции
    waiting_for_admin_confirmation = State()  # Ожидание подтверждения от админа

@router.message(F.text == "Купить билет")
async def buy_ticket(message: types.Message, state: FSMContext):
    # Проверяем, есть ли активные мероприятия
    active_events = get_active_events()  # Функция для получения активных мероприятий
    if not active_events:
        await message.answer(f"Следите за обновлениями в нашем [Telegram-канале](https://t.me/routevents).", reply_markup=get_main_menu(message.chat.id), parse_mode="Markdown")
        return

    # Проверяем, зарегистрирован ли пользователь
    user = get_user(message.from_user.id)  # Функция для получения данных пользователя
    if not user:
        await message.answer("Для покупки билета необходимо зарегистрироваться.")
        await message.answer("Укажите ваше имя и фамилию:")
        await state.set_state(RegistrationStates.waiting_for_name)
    else:
        await show_events(message)

async def show_events(message: types.Message):
    # Показываем список активных мероприятий
    active_events = get_active_events()
    for event in active_events:
        # Создаем inline-кнопку "Купить"
        builder = InlineKeyboardBuilder()
        builder.button(text="Купить", callback_data=f"order_{event['id']}")

        # Проверяем, есть ли фото у мероприятия
        if event.get("photo"):
            # Если фото есть, отправляем его с кнопкой
            await message.answer_photo(
                photo=event["photo"],  # Используем file_id или URL
                caption=f"{event['name']}\n\n{event['description']}\n\nЦена: {event['price']} руб.",
                reply_markup=builder.as_markup()
            )
        else:
            # Если фото нет, отправляем только текст с кнопкой
            await message.answer(
                f"{event['name']}\n\n{event['description']}\n\nЦена: {event['price']} руб.",
                reply_markup=builder.as_markup()
            )

@router.callback_query(F.data.startswith("order_"))
async def process_buy_ticket(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[1])  # Извлекаем ID мероприятия
    event = next((e for e in get_active_events() if e["id"] == event_id), None)

    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="Ознакомился", callback_data=f"buy_{event_id}")
    builder.button(text="Отмена", callback_data="payment_cancelled")
    builder.adjust(2)  # По две кнопки в строке

    await callback.message.answer_document(
        document=FSInputFile("ОСНОВНОЙ_правила_посещения_мероприятия_ROUT_готов.docx"),
        caption=f"**Ознакомьтесь перед покупкой с основными правилами мероприятия «ROUT EVENT»:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

# Обработка нажатия на кнопку "Купить"Основными правилами
@router.callback_query(F.data.startswith("buy_"))
async def process_buy_ticket(callback: types.CallbackQuery, state: FSMContext):
    event_id = int(callback.data.split("_")[1])  # Извлекаем ID мероприятия
    event = next((e for e in get_active_events() if e["id"] == event_id), None)

    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        await callback.answer()
        return

    # Сохраняем данные о мероприятии в состоянии
    await state.update_data(event_id=event_id, event_price=event["price"])

    # Создаем inline-кнопки "Оплатил" и "Отмена"
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплатил", callback_data="payment_confirmed")
    builder.button(text="Отмена", callback_data="payment_cancelled")
    builder.adjust(2)  # По две кнопки в строке

    # Отправляем сообщение с инструкцией по оплате
    await callback.message.answer(
        f"Оплата билета происходит переводом через Т-банк пожертвования.\n\n"
        f"Необходимо перейти по [ссылке]({get_payment_link()}), и пожертвовать {event['price']} руб.",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data == "payment_cancelled")
async def payment_cancelled(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await state.clear()
    await callback.message.answer("Покупка отменена.", reply_markup=get_main_menu(callback.message.chat.id))

# Обработка кнопки "Оплатил"
@router.callback_query(F.data == "payment_confirmed")
async def payment_confirmed(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    event_id = user_data.get("event_id")
    event_price = user_data.get("event_price")

    if not event_id or not event_price:
        await callback.message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    # Запрашиваем скриншот квитанции
    await callback.message.answer("Пожалуйста, пришлите скриншот квитанции об оплате, чтобы мы могли проверить ваш платеж.")
    await state.set_state(PaymentStates.waiting_for_receipt)
    await callback.answer()

# Обработка скриншота квитанции
@router.message(PaymentStates.waiting_for_receipt, F.content_type.in_([ContentType.PHOTO, ContentType.DOCUMENT]))
async def process_receipt(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    event_id = user_data.get("event_id")
    user = get_user(message.from_user.id)

    if not event_id or not user:
        await message.answer("Ошибка: данные не найдены. Попробуйте снова.")
        await state.clear()
        return

    # Получаем данные о мероприятии
    event = get_event_by_id(event_id)
    if not event:
        await message.answer("Мероприятие не найдено.")
        await state.clear()
        return

    # Сохраняем фото квитанции в состоянии
    if message.photo:
        # Если это фото
        receipt_file_id = message.photo[-1].file_id
        await state.update_data(receipt_type='photo', receipt_file_id=receipt_file_id)
    elif message.document:
        # Если это файл
        receipt_file_id = message.document.file_id
        await state.update_data(receipt_type='document', receipt_file_id=receipt_file_id)

    # Уведомляем пользователя
    await message.answer("Спасибо за доверие! Ваш платеж в обработке, скоро отправим ваш билет.")

    # Уведомляем админов и сохраняем ID их сообщений
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить оплату", callback_data=f"confirm_payment_{message.from_user.id}_{event_id}")
    builder.button(text="Отклонить оплату", callback_data=f"disable_payment_{message.from_user.id}_{event_id}")


    data = await state.get_data()
    receipt_type = data.get('receipt_type')
    receipt_file_id = data.get('receipt_file_id')

    for admin_id in ADMINS:
        if receipt_type == 'photo':
            # Отправка фото
            sent_message = await message.bot.send_photo(
                chat_id=admin_id,
                photo=receipt_file_id,
                caption=f"Новый платеж!\n\n"
                        f"Мероприятие: {event['name']}\n"
                        f"Покупатель: {user['full_name']} (@{message.from_user.username})\n"
                        f"Сумма: {event['price']} руб.",
                reply_markup=builder.as_markup()
            )
        elif receipt_type == 'document':
            # Отправка файла
            sent_message = await message.bot.send_document(
                chat_id=admin_id,
                document=receipt_file_id,
                caption=f"Новый платеж!\n\n"
                        f"Мероприятие: {event['name']}\n"
                        f"Покупатель: {user['full_name']} (@{message.from_user.username})\n"
                        f"Сумма: {event['price']} руб.",
                reply_markup=builder.as_markup()
            )

        add_admin_notification(admin_id, sent_message.message_id, message.from_user.id)

    await state.set_state(PaymentStates.waiting_for_admin_confirmation)

# Обработка подтверждения оплаты админом
@router.callback_query(F.data.startswith("confirm_payment_"))
async def confirm_payment(callback: types.CallbackQuery, state: FSMContext):
    # Извлекаем данные из callback_data
    _, _, user_id, event_id = callback.data.split("_")
    user_id = int(user_id)
    event_id = int(event_id)

    # Удаляем уведомления у администраторов
    for admin_id in ADMINS:
        message_ids = get_admin_notifications(admin_id)
        for message_id in message_ids:
            if user_id == message_id['user_id']:
                try:
                    await callback.bot.delete_message(admin_id, message_id['message_id'])
                except Exception as e:
                    print(f"Не удалось удалить сообщение у администратора {admin_id}: {e}")
                delete_admin_notifications(admin_id, user_id)

    # Уведомляем админа, который подтвердил оплату
    await callback.message.answer("Вы успешно подтвердили оплату.")

    add_user_event(user_id=user_id, event_id=event_id)
    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=user_id,
        text="Ваш платеж подтвержден! Билет успешно куплен."
    )

    time.sleep(1.5)

    await generate_and_send_ticket(
        user_id=user_id,
        event_id=event_id,
        callback=callback
    )


    # Очищаем состояние
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("disable_payment_"))
async def disable_payment(callback: types.CallbackQuery, state: FSMContext):
    # Извлекаем данные из callback_data
    _, _, user_id, event_id = callback.data.split("_")
    user_id = int(user_id)
    event_id = int(event_id)

    # Удаляем уведомления у администраторов
    for admin_id in ADMINS:
        message_ids = get_admin_notifications(admin_id)
        for message_id in message_ids:
            if user_id == message_id['user_id']:
                try:
                    await callback.bot.delete_message(admin_id, message_id['message_id'])
                except Exception as e:
                    print(f"Не удалось удалить сообщение у администратора {admin_id}: {e}")
                delete_admin_notifications(admin_id, user_id)

    # Уведомляем админа, который подтвердил оплату
    await callback.message.answer("Вы успешно отклонили оплату.")

    # Уведомляем пользователя
    await callback.bot.send_message(
        chat_id=user_id,
        text="Ваш платеж отклонен! Свяжитесь с менеджером: @rout_manager"
    )

    # Очищаем состояние
    await state.clear()
    await callback.answer()