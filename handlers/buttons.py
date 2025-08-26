# handlers/buttons.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from db import get_role, get_suppliers
import logging

logger = logging.getLogger(__name__)

def manager_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать запрос", callback_data="create_request")],
        [InlineKeyboardButton("Помощь", callback_data="help")]
    ])

def supplier_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Просмотр запросов", callback_data="view_requests")],
        [InlineKeyboardButton("Помощь", callback_data="help")]
    ])

def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Создать запрос", callback_data="create_request")],
        [InlineKeyboardButton("Список пользователей", callback_data="list_users")],
        [InlineKeyboardButton("Помощь", callback_data="help")]
    ])

def menu_for_role(role):
    if role == "manager": return manager_menu()
    if role == "supplier": return supplier_menu()
    if role == "admin": return admin_menu()
    return InlineKeyboardMarkup([])

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    pool = context.bot_data['pool']
    role = await get_role(pool, user_id)
    data = query.data

    if data == "help":
        text = (
            "Менеджер:\n- Создайте запрос через кнопку 'Создать запрос'.\n"
            "Поставщик:\n- Просмотрите запросы через 'Просмотр запросов'.\n"
            "- Для предложения используйте формат: описание, цена."
        )
        await context.bot.send_message(user_id, text)
        return

    if data == "create_request" and role in {"manager", "admin"}:
        await query.message.reply_text("Введите текст запроса:")
        context.user_data['creating_request'] = True
    elif data.startswith("make_offer:") and role in {"supplier", "admin"}:
        req_id = int(data.split(":")[1])
        context.user_data['current_request'] = req_id
        await query.message.reply_text("Введите предложение: описание, цена")
    elif data.startswith("order_offer:") and role in {"manager", "admin"}:
        prop_id = int(data.split(":")[1])
        async with pool.acquire() as conn:
            prop = await conn.fetchrow("SELECT * FROM offers WHERE id=$1", prop_id)
            await conn.execute("UPDATE offers SET status='accepted' WHERE id=$1", prop_id)
            await conn.execute("UPDATE requests SET status='ordered' WHERE id=$1", prop['request_id'])
        await context.bot.send_message(prop['supplier_id'], "Ваше предложение принято!")
        await query.message.reply_text("Заказ оформлен")
    elif data.startswith("reject_offer:") and role in {"manager", "admin"}:
        prop_id = int(data.split(":")[1])
        async with pool.acquire() as conn:
            await conn.execute("UPDATE offers SET status='rejected' WHERE id=$1", prop_id)
        await query.message.reply_text("Предложение отклонено")
    elif data == "list_users" and role == "admin":
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id, username, role, extra_info FROM users")
        text = "\n".join([f"{r['telegram_id']} | {r['username']} | {r['role']} | {r['extra_info']}" for r in rows])
        await context.bot.send_message(user_id, text if text else "Нет пользователей.")