# main.py
import os
import logging
import nest_asyncio
import asyncio
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

from db import get_db_pool, init_db
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

async def main():
    logger.info("Создание пула подключений...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("БД готова")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['pool'] = pool

    # Регистрируем ConversationHandler
    conv = get_conversation_handler()
    app.add_handler(conv)

    # Регистрируем callback и message хендлеры
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    await app.run_polling()
    await pool.close()

# Railway и другие окружения уже могут запускать event loop
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение по сигналу.")