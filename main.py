import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import settings
from .db import init_db
from .handlers.user import router as user_router
from .handlers.admin import router as admin_router

logging.basicConfig(level=logging.INFO)

async def main():
    await init_db()
    bot = Bot(settings.bot_token)
    dp = Dispatcher()
    # Admin first so its callback handlers have priority.
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    print(f"{settings.store_name} bot iniciado.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
