# main.py
import os
import logging
import asyncio
import nest_asyncio

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

# наши модули
from db import get_db_pool, init_db, close_pool
from handlers.start import get_conversation_handler
from handlers.buttons import button_handler
from handlers.messages import message_handler

# Логи
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# patch event loop (Railway любит "уже запущен event loop")
nest_asyncio.apply()

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")


# ----------------- Основная корутина -----------------
async def main():
    logger.info("Создание пула подключений...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("БД готова")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data["pool"] = pool

    # handlers
    conv = get_conversation_handler()
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    try:
        await app.run_polling()
    finally:
        await close_pool(pool)


# ----------------- Запуск -----------------
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