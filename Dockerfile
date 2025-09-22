# ===== Base =====
FROM python:3.11-slim

# Ускорители/чистота логов
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg нужен для конвертации голосовых
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# ===== App =====
WORKDIR /app
# Чтобы python импортировал пакеты из корня (mods/ и т.д.)
ENV PYTHONPATH=/app

# Сначала зависимости (чтобы кешировалось)
COPY requirements.txt .
RUN python -m pip install -r requirements.txt

# Потом весь проект (включая mods/, bot.py, etc.)
COPY . .

# ===== Run (Render Web Service, free) =====
# Render требует, чтобы кто-то слушал $PORT. Поднимем http-сервер + параллельно бота.
CMD sh -c "python -m http.server \$PORT & python bot.py"
