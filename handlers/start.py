# handlers/start.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, CommandHandler, filters
)
from db import add_user
from menus import menu_for_role

# Состояния ConversationHandler
ROLE, EXTRA_INFO = range(2)

ADMIN_IDS = [374728252]

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартовая команда: проверка роли или начало регистрации"""
    user_id = update.message.from_user.id
    pool = context.bot_data['pool']

    # Если админ
    if user_id in ADMIN_IDS:
        await add_user(pool, user_id, update.message.from_user.username, "admin", "Admin")
        await update.message.reply_text("Вы админ! Вот ваше меню:", reply_markup=menu_for_role("admin"))
        return ConversationHandler.END

    # Если обычный юзер — предлагаем выбор роли
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Менеджер", callback_data="role_manager")],
        [InlineKeyboardButton("Поставщик", callback_data="role_supplier")]
    ])
    await update.message.reply_text("Выберите вашу роль:", reply_markup=keyboard)
    return ROLE


async def role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора роли"""
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
    """Сохраняем дополнительную информацию о пользователе"""
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    extra_info = update.message.text
    role = context.user_data.get('role')
    pool = context.bot_data['pool']

    await add_user(pool, user_id, username, role, extra_info)
    await update.message.reply_text(
        f"Регистрация завершена. Ваша роль: {role}.",
        reply_markup=menu_for_role(role)
    )
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена регистрации"""
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END


def get_conversation_handler():
    """Возвращает ConversationHandler для регистрации"""
    return ConversationHandler(
        entry_points=[MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start_handler)],
        states={
            ROLE: [CallbackQueryHandler(role_handler, pattern="^role_")],
            EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_info_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)]
    )