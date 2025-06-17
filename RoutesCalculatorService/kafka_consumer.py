import asyncio
import json
import logging
import os
from typing import Any, Dict

from a_star import a_star_search_algorithm  # Алгоритм A*
from aiokafka import AIOKafkaConsumer

# Импортируем наши модули
from data_models import PortData  # Используем модели из data_models.py
from db_interface import (  # Функции для работы с БД
    get_all_ports_for_algorithm,
    get_port_by_id,
    get_segments_for_port,
    update_calculation_task,
)
from pydantic import ValidationError  # Для обработки ошибок Pydantic

# from .redis_client import update_task_status_in_redis, clear_task_status_from_redis # Для будущего

logger = logging.getLogger("calculator_consumer")  # Даем имя логгеру

# Конфигурация Kafka
KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "kafka:9092")
KAFKA_REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "route_calculation_requests")
KAFKA_CONSUMER_GROUP_ID = os.getenv(
    "KAFKA_CONSUMER_GROUP_ID", "route_calculator_group_1"
)

# Статусы задач
PROCESSING_STATUS = "PROCESSING"  # Пока не используется, но понадобится для Redis
COMPLETED_STATUS = "COMPLETED"
FAILED_STATUS = "FAILED"


async def process_message_from_kafka(payload: Dict[str, Any]):
    """
    Обрабатывает сообщение из Kafka: извлекает данные, выполняет расчет A* и обновляет БД.
    """
    task_id = payload.get("task_id")
    start_port_id = payload.get("start_port_id")
    end_port_id = payload.get("end_port_id")

    logger.info(
        f"Consumer: Начало обработки задачи {task_id} для портов {start_port_id} -> {end_port_id}"
    )

    if not all([task_id, isinstance(start_port_id, int), isinstance(end_port_id, int)]):
        logger.error(
            f"Consumer Task {task_id}: Некорректные или неполные данные в сообщении: {payload}"
        )
        # В реальном приложении можно отправить в Dead Letter Queue (DLQ) или записать ошибку в БД
        return  # Прекращаем обработку этого сообщения

    # TODO: Когда будет Redis, здесь можно обновить статус на PROCESSING
    # update_task_status_in_redis(task_id, PROCESSING_STATUS, "В обработке", "Имя_старт_порта", "Имя_конец_порта")
    # Для этого сначала нужно будет получить start_port_dict и end_port_dict

    try:
        # 1. Получаем данные из БД через db_interface (синхронные вызовы)
        # Оборачиваем в asyncio.to_thread для неблокирующей работы в asyncio
        logger.debug(
            f"Task {task_id}: Запрос данных для стартового порта {start_port_id}"
        )
        start_port_dict = await asyncio.to_thread(get_port_by_id, start_port_id)

        logger.debug(f"Task {task_id}: Запрос данных для конечного порта {end_port_id}")
        end_port_dict = await asyncio.to_thread(get_port_by_id, end_port_id)

        logger.debug(f"Task {task_id}: Запрос всех портов для графа A*")
        all_ports_dicts_list = await asyncio.to_thread(get_all_ports_for_algorithm)

        if not start_port_dict or not end_port_dict:
            error_msg = f"Не удалось получить данные для стартового ({start_port_id}) или конечного ({end_port_id}) порта."
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
            )
            return

        if not all_ports_dicts_list:
            error_msg = "Не удалось получить список всех портов для алгоритма A*."
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
            )
            return

        # 2. Преобразуем данные в Pydantic модели
        try:
            start_port_pydantic = PortData(**start_port_dict)
            end_port_pydantic = PortData(**end_port_dict)
            all_ports_map_pydantic: Dict[int, PortData] = {}
            for p_dict in all_ports_dicts_list:
                all_ports_map_pydantic[p_dict["id"]] = PortData(**p_dict)
        except ValidationError as ve:
            error_msg = (
                f"Ошибка валидации данных порта при преобразовании в Pydantic: {ve}"
            )
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
            )
            return

        # Проверка, что стартовый и конечный порты есть в загруженном графе (после валидации)
        if (
            start_port_id not in all_ports_map_pydantic
            or end_port_id not in all_ports_map_pydantic
        ):
            error_msg = f"Стартовый ({start_port_id}) или конечный ({end_port_id}) порт отсутствует в отвалидированном списке всех портов."
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
            )
            return

        logger.info(f"Task {task_id}: Данные подготовлены, запуск алгоритма A*...")

        # 3. Вызываем алгоритм A* (синхронная CPU-bound функция, выполняем в потоке)
        # get_segments_for_port - это наш callable для получения соседей, он тоже синхронный
        path_objects_pydantic, total_distance = await asyncio.to_thread(
            a_star_search_algorithm,
            start_port_pydantic,
            end_port_pydantic,
            all_ports_map_pydantic,
            get_segments_for_port,  # Передаем синхронную функцию напрямую
        )

        # 4. Обрабатываем результат и обновляем БД
        if path_objects_pydantic and total_distance is not None:
            result_path_ids = [p.id for p in path_objects_pydantic]
            logger.info(
                f"Task {task_id}: Маршрут найден. Дистанция: {total_distance:.2f} nm. Путь (ID портов): {result_path_ids}"
            )
            await asyncio.to_thread(
                update_calculation_task,
                task_id,
                COMPLETED_STATUS,
                result_path_ids,
                total_distance,
            )
        else:
            error_msg = f"Маршрут не найден между портами {start_port_pydantic.name} (ID: {start_port_id}) и {end_port_pydantic.name} (ID: {end_port_id})."
            logger.warning(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
            )

    except Exception as e:
        # Общий обработчик ошибок на случай непредвиденных проблем
        error_msg = f"Неожиданная ошибка при обработке задачи: {str(e)[:500]}"  # Ограничим длину сообщения
        logger.exception(
            f"Task {task_id}: {error_msg}"
        )  # logger.exception выведет traceback
        await asyncio.to_thread(
            update_calculation_task, task_id, FAILED_STATUS, error_message=error_msg
        )

    # TODO: Когда будет Redis, здесь можно очистить промежуточный статус
    # clear_task_status_from_redis(task_id)
    logger.info(f"Consumer: Завершение обработки задачи {task_id}")


async def start_kafka_consumer_loop():
    """
    Основной цикл для запуска и перезапуска Kafka consumer.
    """
    loop = asyncio.get_event_loop()
    consumer = None
    logger.info(
        f"Консьюмер Kafka готовится к запуску для топика '{KAFKA_REQUEST_TOPIC}'..."
    )

    while True:
        try:
            if consumer is None:
                consumer = AIOKafkaConsumer(
                    KAFKA_REQUEST_TOPIC,
                    loop=loop,
                    bootstrap_servers=KAFKA_BROKER_URL,
                    group_id=KAFKA_CONSUMER_GROUP_ID,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                    auto_offset_reset="earliest",
                    enable_auto_commit=True,
                    # Увеличим таймауты, если обработка сообщения может быть долгой
                    # session_timeout_ms=30000, # Таймаут сессии консьюмера
                    # heartbeat_interval_ms=10000, # Как часто отправлять heartbeat
                    # max_poll_interval_ms=300000, # Макс. время между poll(), если обработка долгая
                )

            logger.info(
                f"Попытка подключения консьюмера к Kafka: {KAFKA_BROKER_URL}..."
            )
            await consumer.start()
            logger.info("Консьюмер Kafka успешно подключен и слушает сообщения.")

            async for msg in consumer:
                logger.debug(
                    f"Консьюмером получено сообщение: {msg.topic} p:{msg.partition} o:{msg.offset} key:{msg.key}"
                )
                try:
                    # Запускаем обработку каждого сообщения как отдельную задачу asyncio
                    asyncio.create_task(process_message_from_kafka(msg.value))
                except Exception as task_creation_error:
                    logger.exception(
                        f"Ошибка при создании задачи для обработки сообщения Kafka: {task_creation_error}"
                    )

        except json.JSONDecodeError as e:
            logger.error(
                f"Ошибка декодирования JSON из Kafka: {e}. Сообщение: {getattr(msg, 'value', 'N/A')}"
            )
        except Exception as e:
            logger.exception(
                f"Критическая ошибка в цикле Kafka Consumer: {e}. Перезапуск через 10 секунд..."
            )
            if consumer and consumer.initialized():
                try:
                    await consumer.stop()
                    logger.info("Консьюмер Kafka остановлен из-за ошибки.")
                except Exception as stop_e:
                    logger.error(f"Ошибка при остановке консьюмера Kafka: {stop_e}")
            consumer = None  # Сброс для пересоздания
            await asyncio.sleep(10)
