# main.py
import os
import logging
import asyncio
import nest_asyncio

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

from db import get_db_pool, init_db, close_pool
from handlers.start import get_conversation_handler
from handlers.buttons import button_handler
from handlers.messages import message_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")

# Список админов — можно хранить в ENV и парсить, тут простой пример
DEFAULT_ADMINS = os.getenv("ADMIN_IDS", "374728252")  # строка "id1,id2"
ADMIN_IDS = []
try:
    ADMIN_IDS = [int(x.strip()) for x in DEFAULT_ADMINS.split(",") if x.strip()]
except Exception:
    ADMIN_IDS = [374728252]

async def main():
    logger.info("Создание пула подключений...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("БД готова")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data["pool"] = pool
    app.bot_data["ADMIN_IDS"] = ADMIN_IDS

    # Регистрация хендлеров
    app.add_handler(get_conversation_handler())
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    try:
        await app.run_polling()
    finally:
        await close_pool(pool)

if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка по сигналу")
    finally:
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        logger.info("Event loop остановлен")