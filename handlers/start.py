# handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler, CommandHandler, CallbackQueryHandler, filters
)

import logging
logger = logging.getLogger(__name__)

from db import add_user, get_role
from handlers.buttons import menu_for_role

ROLE, EXTRA_INFO = range(2)

def get_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            ROLE: [CallbackQueryHandler(role_handler, pattern="^role_")],
            EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_info_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)]
    )

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    pool = context.bot_data.get('pool')

    admin_list = context.bot_data.get('ADMIN_IDS', [])

    role_in_db = None
    try:
        if pool:
            role_in_db = await get_role(pool, user_id)
    except Exception:
        logger.exception("Ошибка при проверке роли в БД для %s", user_id)
        role_in_db = None

    if (user_id in admin_list) or (role_in_db == "admin"):
        try:
            if pool:
                await add_user(pool, user_id, user.username, "admin", "Admin")
        except Exception:
            logger.exception("Не удалось добавить/обновить админа в БД: %s", user_id)
        await update.message.reply_text("Вы админ. Вот ваше меню:", reply_markup=menu_for_role("admin"))
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Менеджер", callback_data="role_manager")],
        [InlineKeyboardButton("Поставщик", callback_data="role_supplier")]
    ])
    await update.message.reply_text("Выберите вашу роль:", reply_markup=keyboard)
    return ROLE

async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "role_manager":
        context.user_data['role'] = "manager"
        await query.message.reply_text("Введите ваше имя:")
    else:
        context.user_data['role'] = "supplier"
        await query.message.reply_text("Введите название вашей компании:")
    return EXTRA_INFO

async def extra_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    text = update.message.text.strip() if update.message.text else None
    role = context.user_data.get('role')
    pool = context.bot_data.get('pool')

    if role not in ("manager", "supplier", "admin"):
        await update.message.reply_text("Неверный путь регистрации. Пожалуйста, нажмите /start и выберите роль.")
        return ConversationHandler.END

    try:
        if pool:
            await add_user(pool, user_id, username, role, text)
        else:
            logger.warning("Пул БД не доступен при регистрации пользователя %s", user_id)
    except Exception:
        logger.exception("Ошибка при сохранении пользователя %s", user_id)
        await update.message.reply_text("Произошла ошибка при сохранении данных. Администратор получит лог.")
        return ConversationHandler.END

    try:
        await update.message.reply_text(f"Регистрация завершена. Ваша роль: {role}.", reply_markup=menu_for_role(role))
    except Exception:
        logger.exception("Ошибка при отправке меню пользователю %s", user_id)
        await update.message.reply_text(f"Регистрация завершена. Ваша роль: {role}.")
    return ConversationHandler.END

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END