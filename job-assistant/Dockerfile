# Лёгкий образ для long-polling Telegram-бота.
FROM python:3.12-slim

WORKDIR /app

# Зависимости отдельным слоем — кешируется между сборками
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# БД по умолчанию кладём в /data — смонтируй сюда volume, чтобы данные не терялись:
#   docker run -v job_assistant_data:/data --env-file .env <image>
ENV DB_PATH=/data/job_assistant.db
VOLUME ["/data"]

CMD ["python", "bot.py"]
