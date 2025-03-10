from aiogram import Router
from .start import router as start_router
from .buy_ticket import router as dealers_router
from .feedback import router as promo_router
from .personal_account import router as dice_router
from .event_management import router as event_management_router
from .unknown_commands import router as unknown_commands_router

router = Router()

# Подключаем все роутеры
router.include_router(start_router)
router.include_router(dealers_router)
router.include_router(promo_router)
router.include_router(dice_router)
router.include_router(event_management_router)
router.include_router(unknown_commands_router)