from aiogram import Router, types, F
from aiogram.filters import Command
from pyexpat.errors import messages

from keyboards.main_menu import get_main_menu
from database import  get_ticket_by_id, get_user, get_event_by_id, get_all_used_tickets, add_used_ticket
from config import ADMINS
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardMarkup, KeyboardButton


router = Router()

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.text.startswith("/start ticket_"):
        # Извлекаем ticket_id из команды
        ticket_id = message.text.split("_")[1]

        # Получаем информацию о билете из базы данных
        ticket_info = get_ticket_by_id(ticket_id)
        user = get_user(ticket_info['user_id'])
        event = get_event_by_id(ticket_info['event_id'])
        used = [i[0] for i in get_all_used_tickets()]

        ticket_valid = True
        for i in used:
            if int(ticket_id) == int(i):
                ticket_valid = False


        if ticket_info:
            if message.from_user.id in ADMINS:
                builder = InlineKeyboardBuilder()
                builder.button(text="Использован", callback_data=f"used_ticket_{ticket_id}")

                if ticket_valid:
                    await message.answer(
                        f"🎟 *Информация о билете*\n"
                        f"Имя: {user['full_name']}\n"
                        f"Мероприятие: {event['name']}\n"
                        f"Дата: {event['date']}\n"
                        f"Статус: ✅ Действителен",
                        parse_mode="Markdown", reply_markup=builder.as_markup()
                    )
                else:
                    await message.answer(
                        f"🎟 *Информация о билете*\n"
                        f"Имя: {user['full_name']}\n"
                        f"Мероприятие: {event['name']}\n"
                        f"Дата: {event['date']}\n"
                        f"Статус: ❌ Недействителен",
                        parse_mode="Markdown"
                    )
            else:
                await message.answer(
                    f"🎟 *Информация о билете*\n"
                    f"Имя: {user['full_name']}\n"
                    f"Мероприятие: {event['name']}\n"
                    f"Дата: {event['date']}\n",
                    parse_mode="Markdown"
                )
        else:
            await message.answer("❌ Билет не найден или недействителен.")
    else:
        await message.answer(
            "Привет! Это бот ROUT.\n\n"
            "Здесь вы можете купить билеты на мероприятия, управлять личным кабинетом и оставить отзыв.",
            reply_markup=get_main_menu(message.chat.id)
        )

@router.callback_query(F.data.startswith("used_ticket_"))
async def used_ticket(callback: types.CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])  # Извлекаем ID мероприятия
    await callback.message.answer("Билет успешно использован!")
    add_used_ticket(ticket_id)