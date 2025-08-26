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

# ┏━━━━━━━ Настройка логов ━━━━━━━┓
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway и подобные окружения могут уже запускать event loop
nest_asyncio.apply()

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN or not DATABASE_URL:
    logger.error("BOT_TOKEN или DATABASE_URL не заданы")
    raise RuntimeError("BOT_TOKEN или DATABASE_URL не заданы")

# ┏━━━━━━━ MAIN ━━━━━━━┓
async def main():
    logger.info("Создание пула подключений к БД...")
    pool = await get_db_pool()
    await init_db(pool)
    logger.info("БД готова")

    # Создаём приложение Telegram
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['pool'] = pool

    # Очистка возможного webhook перед polling
    try:
        await app.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook удалён")
    except Exception as e:
        logger.warning(f"Не удалось удалить webhook: {e}")

    # ConversationHandler для регистрации
    conv = get_conversation_handler()
    app.add_handler(conv)

    # Callback и Message хендлеры
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Запуск polling...")
    await app.run_polling()
    logger.info("Polling завершён")

    # Закрытие пула
    await pool.close()
    logger.info("Пул БД закрыт")

# ┏━━━━━━━ Запуск Railway-friendly ━━━━━━━┓
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    # loop.run_forever() оставляем Railway управлять event loop