#!/bin/bash

# -------------------------------
# Скрипт запуска Telegram-бота
# -------------------------------

# Проверка токена
if [ -z "$BOT_TOKEN" ]; then
    echo "Ошибка: переменная окружения BOT_TOKEN не задана!"
    echo "Пример: export BOT_TOKEN='ВАШ_ТОКЕН'"
    exit 1
fi

# Проверка Python3
if ! command -v python3 &> /dev/null
then
    echo "Python3 не найден. Установите Python3 через https://www.python.org/downloads/"
    exit 1
fi

# Проверка pip
if ! command -v pip3 &> /dev/null
then
    echo "pip3 не найден. Установите pip3."
    exit 1
fi

# Установка зависимости python-telegram-bot
echo "Устанавливаем python-telegram-bot, если нужно..."
pip3 install --upgrade python-telegram-bot==20.3

# Путь к файлу бота
BOT_PATH="$HOME/telegram-bot/bot.py"

if [ ! -f "$BOT_PATH" ]; then
    echo "Ошибка: файл бота bot.py не найден в $BOT_PATH"
    echo "Скопируйте bot.py в эту папку: $HOME/telegram-bot/"
    exit 1
fi

# Запуск бота
echo "Запуск бота..."
python3 "$BOT_PATH"