# syntax=docker/dockerfile:1
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

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

EXPOSE 8001