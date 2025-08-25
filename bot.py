#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ----------------------------
# Конфигурация
# ----------------------------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана!")

ADMIN_IDS = {374728252}  # Администратор

ROLE_NAMES = {
    "supplier": "Поставщик",
    "manager": "Менеджер",
    "admin": "Администратор"
}

# ----------------------------
# Логирование
# ----------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------------------
# Хранилище
# ----------------------------
@dataclass
class User:
    tg_id: int
    full_name: str
    username: Optional[str] = None
    role: str = "supplier"

@dataclass
class RequestItem:
    id: int
    manager_id: int
    text: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "open"
    offers: list = field(default_factory=list)  # список id офферов

@dataclass
class Offer:
    id: int
    request_id: int
    supplier_id: int
    price: Optional[str] = None
    brand: Optional[str] = None
    info: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending / accepted / rejected

USERS: Dict[int, User] = {}
REQUESTS: Dict[int, RequestItem] = {}
OFFERS: Dict[int, Offer] = {}
COUNTERS = {"request": 0, "offer": 0}

def next_id(kind: str) -> int:
    COUNTERS[kind] += 1
    return COUNTERS[kind]

def ensure_user_obj(user_id: int, full_name: str, username: Optional[str]) -> User:
    u = USERS.get(user_id)
    if not u:
        role = "admin" if user_id in ADMIN_IDS else "supplier"
        u = User(tg_id=user_id, full_name=full_name, username=username, role=role)
        USERS[user_id] = u
    return u

# ----------------------------
# Главное меню
# ----------------------------
async def show_main_menu(update, user: User):
    buttons = []
    if user.role in ("manager", "admin"):
        buttons.append([InlineKeyboardButton("Создать запрос", callback_data="new_request")])
        buttons.append([InlineKeyboardButton("Мои запросы", callback_data="my_requests")])
    if user.role == "supplier":
        buttons.append([InlineKeyboardButton("Открытые запросы", callback_data="list_requests")])
        buttons.append([InlineKeyboardButton("Мои предложения", callback_data="my_offers")])
    buttons.append([InlineKeyboardButton("Моя роль / ID", callback_data="myid")])
    if user.role == "admin":
        buttons.append([InlineKeyboardButton("Список пользователей", callback_data="user_list")])
    keyboard = InlineKeyboardMarkup(buttons)
    if update.message:
        await update.message.reply_text("Главное меню:", reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Главное меню:", reply_markup=keyboard)

# ----------------------------
# Команды
# ----------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_obj(update.effective_user.id, update.effective_user.full_name, update.effective_user.username)
    await show_main_menu(update, user)

# ----------------------------
# Обработка кнопок
# ----------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = ensure_user_obj(query.from_user.id, query.from_user.full_name, query.from_user.username)

    # --- Создать запрос ---
    if query.data == "new_request":
        await query.message.reply_text("Введите всю информацию по запросу в одном сообщении:")
        return "REQ_INPUT"

    # --- Открытые запросы (поставщик) ---
    elif query.data == "list_requests":
        open_requests = [r for r in REQUESTS.values() if r.status == "open"]
        if not open_requests:
            await query.message.reply_text("Нет открытых запросов.")
            return
        for r in open_requests:
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Сделать предложение", callback_data=f"offer_{r.id}")]])
            await query.message.reply_text(f"🔹 Запрос #{r.id}: {r.text}", reply_markup=kb)

    # --- Мои запросы (менеджер) ---
    elif query.data == "my_requests":
        my_reqs = [r for r in REQUESTS.values() if r.manager_id == user.tg_id]
        if not my_reqs:
            await query.message.reply_text("У вас нет запросов.")
            return
        for r in my_reqs:
            offer_texts = []
            for oid in r.offers:
                off = OFFERS[oid]
                supplier = USERS.get(off.supplier_id)
                offer_texts.append(f"{supplier.full_name}: {off.price} | {off.brand} | {off.info or '-'} | {off.status}")
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("Заказать", callback_data=f"accept_{oid}"),
                                            InlineKeyboardButton("Отклонить", callback_data=f"reject_{oid}")]])
            offers_str = "\n".join(offer_texts) if offer_texts else "Нет предложений"
            await query.message.reply_text(f"🔹 Запрос #{r.id}: {r.text}\nПредложения:\n{offers_str}", reply_markup=kb if offer_texts else None)

    # --- Мои предложения (поставщик) ---
    elif query.data == "my_offers":
        my_offs = [o for o in OFFERS.values() if o.supplier_id == user.tg_id]
        if not my_offs:
            await query.message.reply_text("У вас нет предложений.")
            return
        for o in my_offs:
            r = REQUESTS[o.request_id]
            await query.message.reply_text(f"🔹 Запрос #{r.id}: {r.text}\nВаш оффер: {o.price} | {o.brand} | {o.info or '-'} | {o.status}")

    # --- Моя роль / ID ---
    elif query.data == "myid":
        await query.message.reply_text(f"Ваш ID: {user.tg_id}\nРоль: {ROLE_NAMES.get(user.role, user.role)}")

    # --- Список пользователей (админ) ---
    elif query.data == "user_list" and user.role == "admin":
        if not USERS:
            await query.message.reply_text("Нет зарегистрированных пользователей.")
            return
        for u in USERS.values():
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("Сделать Поставщиком", callback_data=f"role_supplier_{u.tg_id}"),
                 InlineKeyboardButton("Сделать Менеджером", callback_data=f"role_manager_{u.tg_id}")]
            ])
            await query.message.reply_text(f"ID: {u.tg_id}\nИмя: {u.full_name}\nРоль: {ROLE_NAMES.get(u.role, u.role)}", reply_markup=kb)

    # --- Изменение роли пользователя ---
    elif query.data.startswith("role_") and user.role == "admin":
        parts = query.data.split("_")
        new_role, target_id = parts[1], int(parts[2])
        target_user = USERS.get(target_id)
        if target_user:
            old_role = target_user.role
            target_user.role = new_role
            await query.message.reply_text(f"Роль пользователя {target_user.full_name} изменена: {ROLE_NAMES.get(old_role)} → {ROLE_NAMES.get(new_role)}")

    # --- Принять / Отклонить оффер ---
    elif query.data.startswith("accept_") or query.data.startswith("reject_"):
        oid = int(query.data.split("_")[1])
        off = OFFERS.get(oid)
        if not off:
            await query.message.reply_text("Оффер не найден.")
            return
        if query.data.startswith("accept_"):
            off.status = "accepted"
            r = REQUESTS[off.request_id]
            r.status = "closed"
            supplier = USERS.get(off.supplier_id)
            await query.message.reply_text(f"✅ Заказ по офферу #{oid} принят. Поставщик уведомлен.")
            await context.bot.send_message(supplier.tg_id, f"✅ Ваш оффер #{oid} по запросу #{r.id} принят. Заказ оформлен.")
        else:
            off.status = "rejected"
            await query.message.reply_text(f"❌ Оффер #{oid} отклонен.")

# ----------------------------
# Обработка ввода запроса менеджером
# ----------------------------
async def req_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    rid = next_id("request")
    r = RequestItem(id=rid, manager_id=update.effective_user.id, text=text)
    REQUESTS[rid] = r
    await update.message.reply_text(f"🔹 Запрос #{rid} создан!\n{text}")

    # Уведомляем всех поставщиков
    for u in USERS.values():
        if u.role == "supplier":
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("Сделать предложение", callback_data=f"offer_{rid}")]])
            await context.bot.send_message(u.tg_id, f"📢 Новый запрос #{rid}:\n{text}", reply_markup=kb)

# ----------------------------
# Основной запуск
# ----------------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, req_input))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()