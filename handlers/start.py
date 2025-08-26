# handlers/start.py
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, CommandHandler, filters, ContextTypes
from db import add_user, get_role

logger = logging.getLogger(__name__)

ROLE, EXTRA_INFO = range(2)
ADMIN_IDS = [374728252]

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pool = context.bot_data['pool']

    if user_id in ADMIN_IDS:
        await add_user(pool, user_id, update.effective_user.username, "admin", "Admin")
        from handlers.buttons import menu_for_role
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

    if query.data == "role_manager":
        context.user_data['role'] = "manager"
        await query.message.reply_text("Введите ваше имя:")
    else:
        context.user_data['role'] = "supplier"
        await query.message.reply_text("Введите название вашей компании:")

    return EXTRA_INFO

async def extra_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    role = context.user_data.get('role')
    extra_info = update.message.text
    pool = context.bot_data['pool']

    await add_user(pool, user_id, username, role, extra_info)
    from handlers.buttons import menu_for_role
    await update.message.reply_text(f"Регистрация завершена. Ваша роль: {role}.", reply_markup=menu_for_role(role))
    return ConversationHandler.END

async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END

def get_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^/start$") & filters.COMMAND, start_handler)],
        states={
            ROLE: [CallbackQueryHandler(role_handler, pattern="^role_", per_message=True)],
            EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_info_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
        per_message=True
    )