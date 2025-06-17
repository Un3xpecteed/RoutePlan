# syntax=docker/dockerfile:1

FROM python:3.12-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Устанавливаем системные зависимости
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gnupg curl lsb-release ca-certificates \
        build-essential python3-dev libsasl2-dev \
        postgresql-client \
    && \
    curl -fsSL https://packages.confluent.io/clients/deb/archive.key | gpg --dearmor -o /usr/share/keyrings/confluent-archive-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/confluent-archive-keyring.gpg] https://packages.confluent.io/clients/deb $(lsb_release -cs) main" > /etc/apt/sources.list.d/confluent.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends librdkafka-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Единственные добавленные строки: ---
COPY wait-for-it.sh /usr/local/bin/wait-for-it.sh
RUN chmod +x /usr/local/bin/wait-for-it.sh
# ----------------------------------------

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 
# CMD будет определен в docker-compose.yaml