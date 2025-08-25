# Используем slim-образ Python 3.11
FROM python:3.11-slim

# Устанавливаем системные зависимости для asyncpg и сборки пакетов
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Обновляем pip и ставим зависимости
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# Копируем весь проект
COPY . .

# Устанавливаем переменные окружения (можно задать через Railway GUI)
# ENV BOT_TOKEN=your_token_here
# ENV DATABASE_URL=your_database_url_here

# Команда для запуска бота
CMD ["python", "main.py"]