from telegram import InlineKeyboardButton, InlineKeyboardMarkup

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