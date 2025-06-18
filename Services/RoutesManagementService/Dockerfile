# syntax=docker/dockerfile:1
FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE project_config.settings

WORKDIR /app

RUN pip install uv

RUN apk add --no-cache \
    build-base \
    python3-dev \
    postgresql-dev \
    postgresql-client \
    linux-headers \
    librdkafka-dev \
    cyrus-sasl-dev \
&& \
rm -rf /var/cache/apk/*

COPY requirements.txt .
RUN uv pip install -r requirements.txt --system

COPY . .

# Копируем entrypoint.sh и делаем его исполняемым
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 8000

# УДАЛИТЕ ОТСЮДА СТРОКИ ENTRYPOINT и CMD
# ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
# CMD ["gunicorn", "project_config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]