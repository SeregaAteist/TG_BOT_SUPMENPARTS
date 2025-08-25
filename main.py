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

# Читаем переменные окружения (они уже проверяются в db.py, но дублируем для удобства)
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

    # Если нужно — список админов можно положить так (если у тебя есть в конфиге)
    # app.bot_data['ADMIN_IDS'] = [374728252]

    # Регистрируем ConversationHandler для регистрации (из handlers.start)
    conv = get_conversation_handler()
    app.add_handler(conv)

    # Регистрируем callback и message хендлеры
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Запускаем polling...")
    # Запускаем polling (await внутри async main)
    await app.run_polling()
    # После завершения (если ever) закроем пул
    await pool.close()

# Запуск в Railway (или локально)
if __name__ == "__main__":
    # В Railway часто уже есть running loop — используем run_until_complete
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение работы (SIGINT/SIGTERM).")
    finally:
        # на всякий случай — закрыть loop корректно
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        try:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()
        logger.info("Event loop закрыт.")