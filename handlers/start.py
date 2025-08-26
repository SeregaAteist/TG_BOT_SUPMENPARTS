# handlers/start.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, filters
from db import add_user, get_role

ROLE, EXTRA_INFO = range(2)
ADMIN_IDS = [374728252]

def get_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start_handler)],
        states={
            ROLE: [CallbackQueryHandler(role_handler, pattern="^role_")],
            EXTRA_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, extra_info_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel_handler)]
    )

async def start_handler(update, context):
    user_id = update.message.from_user.id
    pool = context.bot_data['pool']

    # Если админ, сразу меню
    if user_id in ADMIN_IDS:
        await add_user(pool, user_id, update.message.from_user.username, "admin", "Admin")
        await update.message.reply_text("Вы админ! Меню:", reply_markup=admin_menu())
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Менеджер", callback_data="role_manager")],
        [InlineKeyboardButton("Поставщик", callback_data="role_supplier")]
    ])
    await update.message.reply_text("Выберите вашу роль:", reply_markup=keyboard)
    return ROLE

async def role_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "role_manager":
        context.user_data['role'] = "manager"
        await query.message.reply_text("Введите ваше имя:")
    else:
        context.user_data['role'] = "supplier"
        await query.message.reply_text("Введите название вашей компании:")
    return EXTRA_INFO

async def extra_info_handler(update, context):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    role = context.user_data['role']
    extra_info = update.message.text
    pool = context.bot_data['pool']

    await add_user(pool, user_id, username, role, extra_info)
    from handlers.buttons import menu_for_role
    await update.message.reply_text(f"Регистрация завершена. Ваша роль: {role}.", reply_markup=menu_for_role(role))
    return ConversationHandler.END

async def cancel_handler(update, context):
    await update.message.reply_text("Регистрация отменена.")
    return ConversationHandler.END

def admin_menu():
    from handlers.buttons import admin_menu as am
    return am()