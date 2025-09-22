FROM python:3.11-slim

# ffmpeg нужен для конвертации голосовых
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render Web Service ждёт, что что-то слушает $PORT.
# Поднимем простой http-сервер + параллельно запустим бота-поллинг.
# НИЧЕГО в коде менять не надо.
CMD sh -c "python -m http.server \$PORT & python bot.py"
