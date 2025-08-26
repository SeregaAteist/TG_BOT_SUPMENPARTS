# main.py
import os
import logging
import nest_asyncio
import asyncio

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters, CommandHandler

from db import get_db_pool, init_db, close_pool
from handlers.start import get_conversation_handler
from handlers.buttons import button_handler
from handlers.messages import message_handler
from utils.logging_setup import setup_logging

# Логи
setup_logging()
logger = logging.getLogger(__name__)

# Разрешаем вложенные loop (Railway-friendly)
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")

# Глобальная переменная для пула (чтобы можно было при необходимости закрыть)
GLOBAL_DB_POOL = None

async def _start_app():
    global GLOBAL_DB_POOL
    # Создаём пул с retry
    pool = await get_db_pool()
    GLOBAL_DB_POOL = pool
    await init_db(pool)

    # Создаём приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['pool'] = pool

    # Регистрируем handlers
    app.add_handler(get_conversation_handler())
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Простая команда healthcheck
    async def ping(update, context):
        await update.message.reply_text("PONG")
    app.add_handler(CommandHandler("ping", ping))

    logger.info("Запускаем polling...")
    await app.run_polling()
    logger.info("Polling завершился, закрываем пул...")
    await close_pool(pool)

def run():
    # Запуск main как таск в уже существующем loop (Railway-friendly)
    loop = asyncio.get_event_loop()
    loop.create_task(_start_app())
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал завершения, пытаемся аккуратно закрыть пул...")
        # Закрываем пул синхронно
        try:
            if GLOBAL_DB_POOL is not None:
                loop.run_until_complete(close_pool(GLOBAL_DB_POOL))
        except Exception as e:
            logger.warning(f"Ошибка при закрытии пула: {e!r}")

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass