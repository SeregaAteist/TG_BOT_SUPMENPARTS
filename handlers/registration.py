from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from db import add_user
from menus import menu_for_role

ROLE, EXTRA_INFO = range(2)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    pool = context.bot_data['pool']

    if user_id in context.bot_data.get('admin_ids', []):
        await add_user(pool, user_id, update.message.from_user.username, "admin", "Admin")
        await update.message.reply_text("Вы админ! Вот ваше меню:", reply_markup=menu_for_role("admin"))
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
    context.user_data['role'] = "manager" if query.data == "role_manager" else "supplier"
    msg = "Введите ваше имя:" if query.data == "role_manager" else "Введите название вашей компании:"
    await query.message.reply_text(msg)
    return EXTRA_INFO

async def extra_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    extra_info = update.message.text
    role = context.user_data.get('role')
    pool = context.bot_data['pool']

    await add_user(pool, user_id, username, role, extra_info)
    await update.message.reply_text(f"Регистрация завершена. Ваша роль: {role}.",
                                    reply_markup=menu_for_role(role))
    return ConversationHandler.END

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END