# handlers/buttons.py
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import get_role, get_suppliers, create_offer, get_user_by_telegram_id, create_request

logger = logging.getLogger(__name__)

# Меню для ролей
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

# Обработчик нажатий кнопок — централизованно
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user_id = query.from_user.id
    pool = context.bot_data.get('pool')
    role = None
    try:
        if pool:
            role = await get_role(pool, user_id)
    except Exception:
        logger.exception("Не удалось получить роль для %s", user_id)
        role = None

    data = query.data or ""

    # Помощь
    if data == "help":
        if role == "manager":
            text = ("Менеджер:\n"
                    "- Нажмите 'Создать запрос' и отправьте весь текст запроса одним сообщением.\n"
                    "- Когда придут предложения, вы сможете 'Заказать' или 'Отклонить'.")
        elif role == "supplier":
            text = ("Поставщик:\n"
                    "- Нажмите 'Просмотр запросов' чтобы увидеть доступные запросы.\n"
                    "- Для ответа используйте формат: описание, цена")
        else:
            text = "Выберите действие из меню."
        await query.message.reply_text(text)
        return

    # Менеджер — создание запроса
    if data == "create_request" and role in {"manager", "admin"}:
        await query.message.reply_text("Введите текст запроса одним сообщением:")
        context.user_data['creating_request'] = True
        return

    # Просмотр запросов (поставщик)
    if data == "view_requests" and role in {"supplier", "admin"}:
        # упрощённо: покажем последние 10 запросов без пагинации
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, content, created_at FROM requests WHERE status='new' ORDER BY created_at DESC LIMIT 10")
        if not rows:
            await query.message.reply_text("Нет актуальных запросов.")
            return
        for r in rows:
            kb = [[InlineKeyboardButton("Сделать предложение", callback_data=f"make_offer:{r['id']}")]]
            await query.message.reply_text(f"#{r['id']}: {r['content']}", reply_markup=InlineKeyboardMarkup(kb))
        return

    # Поставщик — сделать предложение
    if data.startswith("make_offer:") and role in {"supplier", "admin"}:
        req_id = int(data.split(":", 1)[1])
        context.user_data['current_request'] = req_id
        await query.message.reply_text("Введите предложение в формате: описание, цена")
        return

    # Заказ / Отклонение (менеджер)
    if data.startswith("order_offer:") and role in {"manager", "admin"}:
        prop_id = int(data.split(":", 1)[1])
        async with pool.acquire() as conn:
            prop = await conn.fetchrow("SELECT * FROM offers WHERE id=$1", prop_id)
            if not prop:
                await query.message.reply_text("Предложение не найдено.")
                return
            await conn.execute("UPDATE offers SET status='accepted' WHERE id=$1", prop_id)
            await conn.execute("UPDATE requests SET status='ordered' WHERE id=$1", prop['request_id'])
        try:
            await context.bot.send_message(prop['supplier_id'], "Ваше предложение принято! Менеджер оформил заказ.")
        except Exception:
            logger.exception("Не удалось отправить уведомление поставщику %s", prop['supplier_id'])
        await query.message.reply_text("Заказ оформлен")
        return

    if data.startswith("reject_offer:") and role in {"manager", "admin"}:
        prop_id = int(data.split(":", 1)[1])
        async with pool.acquire() as conn:
            await conn.execute("UPDATE offers SET status='rejected' WHERE id=$1", prop_id)
        await query.message.reply_text("Предложение отклонено")
        return

    # Список пользователей (admin)
    if data == "list_users" and role == "admin":
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id, username, role, extra_info FROM users ORDER BY created_at DESC LIMIT 200")
        text = "\n".join([f"{r['telegram_id']} | {r['username']} | {r['role']} | {r['extra_info']}" for r in rows])
        await query.message.reply_text(text or "Нет пользователей.")
        return

    # По умолчанию — ничего
    await query.message.reply_text("Неизвестная команда.")