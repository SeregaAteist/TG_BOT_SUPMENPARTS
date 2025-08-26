
import os
import asyncio
import logging
import asyncpg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CallbackQueryHandler,
    MessageHandler, filters
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_IDS = [374728252]

# ------------------ База ------------------
async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            username TEXT,
            role TEXT
        );
        CREATE TABLE IF NOT EXISTS requests(
            id SERIAL PRIMARY KEY,
            manager_id BIGINT REFERENCES users(telegram_id),
            content TEXT,
            status TEXT DEFAULT 'new'
        );
        CREATE TABLE IF NOT EXISTS offers(
            id SERIAL PRIMARY KEY,
            request_id INT REFERENCES requests(id) ON DELETE CASCADE,
            supplier_id BIGINT REFERENCES users(telegram_id),
            content TEXT,
            price NUMERIC,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

# ------------------ Хендлеры ------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [InlineKeyboardButton("Создать запрос", callback_data="create_request")]
    ]
    await update.message.reply_text("Главное меню:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "create_request":
        await query.message.reply_text("Введите весь текст запроса в одном сообщении:")
        context.user_data['creating_request'] = True

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pool = context.bot_data['pool']

    if context.user_data.get('creating_request'):
        text = update.message.text
        async with pool.acquire() as conn:
            req_id = await conn.fetchval(
                "INSERT INTO requests(manager_id, content) VALUES($1,$2) RETURNING id",
                user_id, text
            )
            suppliers = await conn.fetch("SELECT telegram_id FROM users WHERE role='supplier'")
        for s in suppliers:
            kb = [[InlineKeyboardButton("Сделать предложение", callback_data=f"make_offer:{req_id}")]]
            await context.bot.send_message(s['telegram_id'], f"Новый запрос: {text}", reply_markup=InlineKeyboardMarkup(kb))
        context.user_data['creating_request'] = False
        await update.message.reply_text("Запрос отправлен поставщикам!")

# ------------------ MAIN ------------------
async def main():
    pool = await get_db_pool()
    await init_db(pool)

    # Добавляем админа в БД, если его нет
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users(telegram_id, role) VALUES($1,'admin')
            ON CONFLICT(telegram_id) DO NOTHING
        """, ADMIN_IDS[0])

    app = ApplicationBuilder().token(TOKEN).build()
    app.bot_data['pool'] = pool

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())