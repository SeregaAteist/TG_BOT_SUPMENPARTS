import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import asyncpg

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

async def get_db_pool():
    return await asyncpg.create_pool(DATABASE_URL)

async def init_db():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            telegram_id BIGINT UNIQUE,
            role TEXT
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS requests(
            id SERIAL PRIMARY KEY,
            manager_id BIGINT,
            content TEXT,
            status TEXT DEFAULT 'open'
        );
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS offers(
            id SERIAL PRIMARY KEY,
            request_id INT REFERENCES requests(id),
            supplier_id BIGINT,
            content TEXT,
            status TEXT DEFAULT 'pending'
        );
        """)
    return pool

def main_menu(role):
    buttons = []
    if role == 'manager':
        buttons.append([InlineKeyboardButton("Создать запрос", callback_data="create_request")])
        buttons.append([InlineKeyboardButton("Мои запросы", callback_data="my_requests")])
    elif role == 'supplier':
        buttons.append([InlineKeyboardButton("Сделать предложение", callback_data="view_requests")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['db_pool']
    user_id = update.effective_user.id
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", user_id)
        if not user:
            await conn.execute("INSERT INTO users(telegram_id, role) VALUES($1,$2)", user_id, 'supplier')
            role = 'supplier'
        else:
            role = user['role']
    await update.message.reply_text(f"Привет! Ваша роль: {role.capitalize()}", reply_markup=main_menu(role))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pool = context.bot_data['db_pool']
    user_id = query.from_user.id

    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id=$1", user_id)
        role = user['role']

    if query.data == "create_request" and role=="manager":
        await query.message.reply_text("Напишите текст запроса:")
        context.user_data['action'] = 'creating_request'

    elif query.data == "my_requests" and role=="manager":
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM requests WHERE manager_id=$1", user_id)
            if not rows:
                await query.message.reply_text("У вас пока нет запросов.")
            else:
                for r in rows:
                    offers = await conn.fetch("SELECT * FROM offers WHERE request_id=$1", r['id'])
                    if offers:
                        msg = f"Запрос: {r['content']}\nПредложения:\n"
                        buttons = []
                        for o in offers:
                            msg += f"- {o['content']} (от {o['supplier_id']})\n"
                            buttons.append([
                                InlineKeyboardButton(f"Заказать {o['id']}", callback_data=f"accept_{o['id']}"),
                                InlineKeyboardButton(f"Отклонить {o['id']}", callback_data=f"reject_{o['id']}")
                            ])
                        await query.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))
                    else:
                        await query.message.reply_text(f"Запрос: {r['content']}\nПредложений нет.")

    elif query.data == "view_requests" and role=="supplier":
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM requests WHERE status='open'")
            if not rows:
                await query.message.reply_text("Нет доступных запросов.")
            else:
                msg = "Доступные запросы:\n"
                for r in rows:
                    msg += f"ID {r['id']}: {r['content']}\n"
                await query.message.reply_text(msg)
                context.user_data['action'] = 'making_offer'

    elif query.data.startswith("accept_") and role=="manager":
        offer_id = int(query.data.split("_")[1])
        async with pool.acquire() as conn:
            offer = await conn.fetchrow("SELECT * FROM offers WHERE id=$1", offer_id)
            if offer:
                await conn.execute("UPDATE offers SET status='accepted' WHERE id=$1", offer_id)
                await conn.execute("UPDATE requests SET status='closed' WHERE id=$1", offer['request_id'])
                supplier_id = offer['supplier_id']
                await context.bot.send_message(chat_id=supplier_id, text=f"Ваше предложение по запросу {offer['request_id']} принято!")
        await query.message.reply_text("Заказ подтвержден.")

    elif query.data.startswith("reject_") and role=="manager":
        offer_id = int(query.data.split("_")[1])
        async with pool.acquire() as conn:
            await conn.execute("UPDATE offers SET status='rejected' WHERE id=$1", offer_id)
        await query.message.reply_text("Предложение отклонено.")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = context.bot_data['db_pool']
    user_id = update.effective_user.id
    text = update.message.text
    action = context.user_data.get('action')

    if action == 'creating_request':
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO requests(manager_id, content) VALUES($1,$2)", user_id, text)
        await update.message.reply_text("Запрос создан и отправлен поставщикам!")
        context.user_data['action'] = None

    elif action == 'making_offer':
        async with pool.acquire() as conn:
            request = await conn.fetchrow("SELECT * FROM requests WHERE status='open' ORDER BY id DESC LIMIT 1")
            if request:
                await conn.execute("INSERT INTO offers(request_id, supplier_id, content) VALUES($1,$2,$3)",
                                   request['id'], user_id, text)
                await update.message.reply_text("Предложение отправлено менеджеру!")
        context.user_data['action'] = None

async def main():
    pool = await init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.bot_data['db_pool'] = pool

    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(MessageHandler(filters.COMMAND, start))

    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())