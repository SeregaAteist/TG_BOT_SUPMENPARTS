# handlers/messages.py
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import create_request, get_suppliers, create_offer

logger = logging.getLogger(__name__)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    pool = context.bot_data.get('pool')

    # Менеджер создаёт запрос (одним сообщением)
    if context.user_data.get('creating_request'):
        context.user_data['creating_request'] = False
        if not pool:
            await update.message.reply_text("База данных недоступна — попробуйте позже.")
            return
        try:
            req_id = await create_request(pool, user_id, text)
            suppliers = await get_suppliers(pool)
        except Exception:
            logger.exception("Ошибка при создании запроса")
            await update.message.reply_text("Ошибка при создании запроса. Админ получит лог.")
            return

        if not suppliers:
            await update.message.reply_text("Поставщики не найдены.")
            return

        for s_id in suppliers:
            kb = [[InlineKeyboardButton("Сделать предложение", callback_data=f"make_offer:{req_id}")]]
            try:
                await context.bot.send_message(s_id, f"Новый запрос #{req_id}: {text}", reply_markup=InlineKeyboardMarkup(kb))
            except Exception:
                logger.exception("Не удалось отправить запрос поставщику %s", s_id)

        await update.message.reply_text("Запрос отправлен поставщикам!")
        return

    # Поставщик отвечает на текущий запрос (в context.user_data['current_request'])
    if 'current_request' in context.user_data:
        req_id = context.user_data.pop('current_request')
        try:
            description, price = map(str.strip, text.split(",", 1))
            price = float(price)
            if price <= 0:
                raise ValueError("price <= 0")
        except Exception:
            await update.message.reply_text("Неверный формат. Используйте: описание, цена (например: 'Клапан, 1234.56')")
            return

        if not pool:
            await update.message.reply_text("База данных недоступна — попробуйте позже.")
            return

        try:
            prop_id = await create_offer(pool, req_id, user_id, description, price)
            # получить manager id чтобы переслать предложение
            async with pool.acquire() as conn:
                mgr_id = await conn.fetchval("SELECT manager_id FROM requests WHERE id=$1", req_id)
        except Exception:
            logger.exception("Ошибка при создании предложения")
            await update.message.reply_text("Ошибка при отправке предложения. Админ получит лог.")
            return

        kb = [[
            InlineKeyboardButton("Заказать", callback_data=f"order_offer:{prop_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_offer:{prop_id}")
        ]]
        try:
            await context.bot.send_message(mgr_id, f"Поступило предложение: {description}, {price}", reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            logger.exception("Не удалось отправить предложение менеджеру %s", mgr_id)
        await update.message.reply_text("Предложение отправлено менеджеру!")
        return

    # Если ни одна логика не сработала — информируем
    await update.message.reply_text("Не понимаю — используйте меню или /start.")