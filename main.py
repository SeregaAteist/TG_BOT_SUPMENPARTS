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

    # Callback и message handlers
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Бот запущен...")
    await app.run_polling()
    await pool.close()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение по сигналу.")
    finally:
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        logger.info("Event loop остановлен.")