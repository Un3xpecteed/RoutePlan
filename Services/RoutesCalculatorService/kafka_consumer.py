# RoutesCalculatorService/kafka_consumer.py
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from a_star import a_star_search_algorithm
from aiokafka import AIOKafkaConsumer
from data_models import PortData, SegmentDataForAStar
from db_interface import (
    get_all_ports_for_algorithm,
    get_port_by_id,
    get_segments_for_port,
    update_calculation_task,
)
from pydantic import ValidationError

logger = logging.getLogger("calculator_consumer")

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "kafka:9092")
KAFKA_REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "route_calculation_requests")
KAFKA_CONSUMER_GROUP_ID = os.getenv(
    "KAFKA_CONSUMER_GROUP_ID", "route_calculator_group_1"
)

PROCESSING_STATUS = "PROCESSING"
COMPLETED_STATUS = "COMPLETED"
FAILED_STATUS = "FAILED"


async def process_message_from_kafka(payload: Dict[str, Any]):
    """
    Обрабатывает сообщение из Kafka: извлекает данные, выполняет расчет A* и обновляет БД.
    """
    task_id = payload.get("task_id")
    start_port_id = payload.get("start_port_id")
    end_port_id = payload.get("end_port_id")
    vessel_speed_knots = payload.get("vessel_speed_knots")  # Получаем скорость

    logger.info(
        f"Consumer: Начало обработки задачи {task_id} для портов {start_port_id} -> {end_port_id}"
        f" (Скорость судна: {vessel_speed_knots or 'не указана'})"
    )

    if not all([task_id, isinstance(start_port_id, int), isinstance(end_port_id, int)]):
        logger.error(
            f"Consumer Task {task_id}: Некорректные или неполные данные в сообщении: {payload}"
        )
        return

    try:
        # 1. Получаем данные из БД через db_interface (синхронные вызовы)
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
                update_calculation_task,
                task_id,
                FAILED_STATUS,
                error_message=error_msg,
                vessel_speed_knots=vessel_speed_knots,
            )
            return

        if not all_ports_dicts_list:
            error_msg = "Не удалось получить список всех портов для алгоритма A*."
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task,
                task_id,
                FAILED_STATUS,
                error_message=error_msg,
                vessel_speed_knots=vessel_speed_knots,
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
                update_calculation_task,
                task_id,
                FAILED_STATUS,
                error_message=error_msg,
                vessel_speed_knots=vessel_speed_knots,
            )
            return

        if (
            start_port_id not in all_ports_map_pydantic
            or end_port_id not in all_ports_map_pydantic
        ):
            error_msg = f"Стартовый ({start_port_id}) или конечный ({end_port_id}) порт отсутствует в отвалидированном списке всех портов."
            logger.error(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task,
                task_id,
                FAILED_STATUS,
                error_message=error_msg,
                vessel_speed_knots=vessel_speed_knots,
            )
            return

        logger.info(f"Task {task_id}: Данные подготовлены, запуск алгоритма A*...")

        # 3. Вызываем алгоритм A*
        path_objects_pydantic, total_distance = await asyncio.to_thread(
            a_star_search_algorithm,
            start_port_pydantic,
            end_port_pydantic,
            all_ports_map_pydantic,
            get_segments_for_port,
        )

        result_waypoints_data: Optional[List[Dict[str, Any]]] = None
        if path_objects_pydantic and total_distance is not None:
            result_path_ids = [p.id for p in path_objects_pydantic]

            # ИЗМЕНЕНИЕ ЛОГИКИ: вместо ETA/ETD, записываем сегментные дистанции и время
            if vessel_speed_knots is not None and vessel_speed_knots > 0:
                result_waypoints_data = []
                for i, port_obj in enumerate(path_objects_pydantic):
                    waypoint_segment_info = {
                        "port_id": port_obj.id,
                        "port_name": port_obj.name,
                        "latitude": port_obj.latitude,
                        "longitude": port_obj.longitude,
                        "segment_distance_nm": 0.0,  # Дистанция до этого порта
                        "segment_travel_hours": 0.0,  # Время в пути до этого порта
                        "total_distance_from_start_nm": 0.0,  # Общая дистанция от начала
                        "total_travel_hours_from_start": 0.0,  # Общее время от начала
                    }

                    if i > 0:
                        prev_port = path_objects_pydantic[i - 1]
                        segments_from_prev = await asyncio.to_thread(
                            get_segments_for_port, prev_port.id
                        )
                        segment_to_current = next(
                            (
                                SegmentDataForAStar(**s)
                                for s in segments_from_prev
                                if s["PortOfArrival_id"] == port_obj.id
                            ),
                            None,
                        )

                        if segment_to_current:
                            segment_distance = segment_to_current.distance
                            travel_hours = segment_distance / vessel_speed_knots

                            waypoint_segment_info["segment_distance_nm"] = round(
                                segment_distance, 2
                            )
                            waypoint_segment_info["segment_travel_hours"] = round(
                                travel_hours, 2
                            )

                            # Накапливаем общие значения
                            waypoint_segment_info["total_distance_from_start_nm"] = (
                                round(
                                    result_waypoints_data[i - 1][
                                        "total_distance_from_start_nm"
                                    ]
                                    + segment_distance,
                                    2,
                                )
                            )
                            waypoint_segment_info["total_travel_hours_from_start"] = (
                                round(
                                    result_waypoints_data[i - 1][
                                        "total_travel_hours_from_start"
                                    ]
                                    + travel_hours,
                                    2,
                                )
                            )
                        else:
                            logger.warning(
                                f"Task {task_id}: Не найден сегмент от порта {prev_port.name} (ID: {prev_port.id}) к порту {port_obj.name} (ID: {port_obj.id}) для расчета сегментных данных."
                            )
                            # Если сегмент не найден, сбрасываем значения, чтобы не было NaN
                            waypoint_segment_info["segment_distance_nm"] = 0.0
                            waypoint_segment_info["segment_travel_hours"] = 0.0
                            waypoint_segment_info["total_distance_from_start_nm"] = (
                                result_waypoints_data[i - 1][
                                    "total_distance_from_start_nm"
                                ]
                            )
                            waypoint_segment_info["total_travel_hours_from_start"] = (
                                result_waypoints_data[i - 1][
                                    "total_travel_hours_from_start"
                                ]
                            )

                    result_waypoints_data.append(waypoint_segment_info)

            # 5. Обновляем БД
            logger.info(
                f"Task {task_id}: Маршрут найден. Дистанция: {total_distance:.2f} nm. "
                f"Путь (ID портов): {result_path_ids}"
            )
            if result_waypoints_data:
                logger.info(
                    f"Task {task_id}: Сегментные данные и время рассчитаны. {len(result_waypoints_data)} вейпоинтов."
                )

            await asyncio.to_thread(
                update_calculation_task,
                task_id,
                COMPLETED_STATUS,
                result_path_ids,
                total_distance,
                result_waypoints_data,  # Передаем новые данные
                vessel_speed_knots,
            )
        else:
            error_msg = f"Маршрут не найден между портами {start_port_pydantic.name} (ID: {start_port_id}) и {end_port_pydantic.name} (ID: {end_port_id})."
            logger.warning(f"Task {task_id}: {error_msg}")
            await asyncio.to_thread(
                update_calculation_task,
                task_id,
                FAILED_STATUS,
                error_message=error_msg,
                vessel_speed_knots=vessel_speed_knots,
            )

    except Exception as e:
        error_msg = f"Неожиданная ошибка при обработке задачи: {str(e)[:500]}"
        logger.exception(f"Task {task_id}: {error_msg}")
        await asyncio.to_thread(
            update_calculation_task,
            task_id,
            FAILED_STATUS,
            error_message=error_msg,
            vessel_speed_knots=vessel_speed_knots,
        )

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
            consumer = None
            await asyncio.sleep(10)
