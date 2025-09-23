# ===== Base =====
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg нужен для конвертации голосовых
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# ===== App =====
WORKDIR /app
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY . .

# ===== Run =====
CMD ["python", "bot.py"]
