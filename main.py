# main.py
import os
import logging
import nest_asyncio
import asyncio

from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

# наши модули
from db import get_db_pool, init_db
from handlers.start import get_conversation_handler
from handlers.buttons import button_handler
from handlers.messages import message_handler

# Настройка логов
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway и подобные окружения иногда уже запускают event loop.
# nest_asyncio позволяет корректно встраивать наш loop в такое окружение.
nest_asyncio.apply()

# Читаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы в переменных окружения")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")

# MAIN
async def main():
    # Инициализируем пул базы и таблицы
    logger.info("Создаём пул подключений к БД...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("Пул и таблицы готовы")

    # Создаём приложение Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Кладём пул в bot_data чтобы хендлеры могли достать
    app.bot_data['pool'] = pool

    # Регистрируем ConversationHandler для регистрации (из handlers.start)
    conv = get_conversation_handler()
    app.add_handler(conv)

    # Регистрируем callback и message хендлеры
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    await app.run_polling()
    await pool.close()

# Запуск в Railway (или локально)
if __name__ == "__main__":
    import asyncio
    import nest_asyncio

    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.create_task(main())