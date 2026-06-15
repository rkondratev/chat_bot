import asyncio
import logging

from aiogram import Bot, Dispatcher

from env import BOT_TOKEN
from handlers import router
from database import init_db, close_db

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    await init_db()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    logging.info("ЗАПУСК БОТА")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("БОТ ОСТАНОВЛЕН")
    finally:
        asyncio.run(close_db())
