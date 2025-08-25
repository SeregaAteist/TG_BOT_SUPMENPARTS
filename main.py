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
from utils.logging_setup import setup_logging

# Настройка логов
setup_logging()
logger = logging.getLogger(__name__)

# Разрешаем вложенные event loop для Railway / CI
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы в переменных окружения")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")

async def main():
    logger.info("Создаём пул подключений к БД...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("Пул и таблицы готовы")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['pool'] = pool

    # ConversationHandler для регистрации
    conv_handler = get_conversation_handler()
    app.add_handler(conv_handler)

    # Callback и Message хендлеры
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Healthcheck
    async def ping(update, context):
        await update.message.reply_text("PONG")

    from telegram.ext import CommandHandler
    app.add_handler(CommandHandler("ping", ping))

    logger.info("Запускаем polling...")
    await app.run_polling()
    await pool.close()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())