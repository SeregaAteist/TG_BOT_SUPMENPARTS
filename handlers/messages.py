# handlers/messages.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_role, get_suppliers

async def message_handler(update, context):
    user_id = update.message.from_user.id
    text = update.message.text
    pool = context.bot_data['pool']
    role = await get_role(pool, user_id)

    if context.user_data.get('creating_request'):
        context.user_data['creating_request'] = False
        async with pool.acquire() as conn:
            req_id = await conn.fetchval(
                "INSERT INTO requests(manager_id, content) VALUES($1,$2) RETURNING id",
                user_id, text
            )
            suppliers = await get_suppliers(pool)
        for s_id in suppliers:
            kb = [[InlineKeyboardButton("Сделать предложение", callback_data=f"make_offer:{req_id}")]]
            await context.bot.send_message(s_id, f"Новый запрос: {text}", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("Запрос отправлен поставщикам!")

    elif 'current_request' in context.user_data:
        req_id = context.user_data.pop('current_request')
        try:
            description, price = map(str.strip, text.split(",", 1))
            price = float(price)
            if price <= 0:
                raise ValueError()
        except:
            await update.message.reply_text("Неверный формат. Используйте: описание, цена (цена > 0)")
            return
        async with pool.acquire() as conn:
            prop_id = await conn.fetchval(
                "INSERT INTO offers(request_id, supplier_id, content, price) VALUES($1,$2,$3,$4) RETURNING id",
                req_id, user_id, description, price
            )
            mgr_id = await conn.fetchval("SELECT manager_id FROM requests WHERE id=$1", req_id)
        kb = [[
            InlineKeyboardButton("Заказать", callback_data=f"order_offer:{prop_id}"),
            InlineKeyboardButton("Отклонить", callback_data=f"reject_offer:{prop_id}")
        ]]
        await context.bot.send_message(mgr_id, f"Поступило предложение: {description}, {price}", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("Предложение отправлено менеджеру!")