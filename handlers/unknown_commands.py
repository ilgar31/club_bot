from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.main_menu import get_main_menu
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Обработка неизвестных команд
@router.message()
async def unknown_command(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Вернуться в главное меню", callback_data="back_to_main_menu")

    await message.answer(
        "Аккуратнее, не сломай меня 🤖\n\n"
        "Чтобы использовать функции - нажимай по кнопкам:)",
        reply_markup=builder.as_markup()
    )

# Обработка кнопки "🔙 Вернуться в главное меню"
@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    # Удаляем предыдущее сообщение
    await callback.message.delete()

    # Отправляем новое сообщение с главным меню
    await callback.message.answer("⚡️ Главное меню ⚡️", reply_markup=get_main_menu(callback.from_user.id))
    await callback.answer()