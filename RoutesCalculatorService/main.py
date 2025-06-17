import asyncio
import logging
from contextlib import asynccontextmanager

from db_interface import check_db_connection
from fastapi import FastAPI
from kafka_consumer import start_kafka_consumer_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    logger.info("Lifespan: Запуск FastAPI приложения (Route Calculator Service)...")

    # УДАЛЯЕМ ЭТУ СТРОКУ: await asyncio.sleep(20) # Больше не нужна, полагаемся на depends_on и цикл ожидания ниже

    logger.info(
        "Lifespan: Проверка соединения с базой данных и ожидание готовности таблиц..."
    )

    # УВЕЛИЧИВАЕМ КОЛИЧЕСТВО ПОПЫТОК И/ИЛИ ЗАДЕРЖКУ
    retries = 60  # Увеличено с 10 до 60 (суммарно 5 минут ожидания)
    delay = 5  # секунд. Можно увеличить до 10, если 5 минут все равно мало.

    for i in range(retries):
        if await asyncio.to_thread(
            check_db_connection
        ):  # check_db_connection уже включает проверку таблицы
            logger.info(
                "Lifespan: Соединение с базой данных успешно проверено и таблицы готовы."
            )
            break
        logger.warning(
            f"Lifespan: База данных не готова или таблицы отсутствуют. Попытка {i + 1}/{retries}. Ожидание {delay} секунд..."
        )
        await asyncio.sleep(delay)
    else:
        logger.error(
            "Lifespan: Критическая ошибка: не удалось подключиться к базе данных или таблицы не появились в срок!"
        )
        raise RuntimeError("Lifespan: Database tables not ready on startup")

    logger.info("Lifespan: Запуск Kafka consumer в фоновой задаче...")
    kafka_consumer_task = asyncio.create_task(start_kafka_consumer_loop())
    logger.info("Lifespan: Фоновая задача Kafka consumer успешно создана.")

    try:
        yield
    finally:
        logger.info(
            "Lifespan: Остановка FastAPI приложения (Route Calculator Service)..."
        )
        if kafka_consumer_task and not kafka_consumer_task.done():
            logger.info("Lifespan: Попытка отмены задачи Kafka consumer...")
            kafka_consumer_task.cancel()
            try:
                await kafka_consumer_task
                logger.info(
                    "Lifespan: Задача Kafka consumer успешно отменена и завершена."
                )
            except asyncio.CancelledError:
                logger.info("Lifespan: Задача Kafka consumer была отменена (ожидаемо).")
            except Exception as e_task_shutdown:
                logger.error(
                    f"Lifespan: Ошибка при ожидании завершения задачи Kafka consumer: {e_task_shutdown}"
                )
        elif kafka_consumer_task and kafka_consumer_task.done():
            logger.info("Lifespan: Задача Kafka consumer уже была завершена.")


app = FastAPI(
    title="Route Calculator Service",
    description="Сервис для асинхронного расчета маршрутов через Kafka.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/", summary="Статус сервиса")
async def root():
    logger.info("Обращение к корневому эндпоинту /")
    return {
        "message": "Route Calculator Service активен. Kafka consumer должен быть активен."
    }


@app.get("/health", summary="Проверка здоровья сервиса")
async def health_check():
    logger.info("Проверка здоровья сервиса /health")
    return {"status": "healthy", "service": "RouteCalculatorService"}
