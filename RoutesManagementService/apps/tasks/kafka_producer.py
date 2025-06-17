# RoutesManagementService/apps/tasks/kafka_producer.py
import json
import logging
import os
import socket
from typing import Optional

from confluent_kafka import KafkaError, Message, Producer

logger = logging.getLogger(__name__)

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "kafka:9092")
REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "route_calculation_requests")

_producer_instance: Optional[Producer] = None


def _delivery_report(err: Optional[KafkaError], msg: Optional[Message]):
    if err is not None:
        logger.error(f"Ошибка доставки сообщения в Kafka: {err}")
    else:
        if msg is not None:
            logger.info(
                f"Сообщение успешно доставлено в топик {msg.topic()} "
                f"раздел [{msg.partition()}] с offset {msg.offset()}"
            )
        else:
            logger.warning(
                "Delivery report вызван без ошибки, но объект сообщения отсутствует."
            )


def get_kafka_producer() -> Producer:
    global _producer_instance
    if _producer_instance is None:
        conf = {
            "bootstrap.servers": KAFKA_BROKER_URL,
            "client.id": socket.gethostname(),
            "enable.idempotence": "true",
            "acks": "all",
            "message.timeout.ms": 30000,
        }
        try:
            _producer_instance = Producer(conf)
            logger.info(
                f"Confluent Kafka Producer сконфигурирован для {KAFKA_BROKER_URL}"
            )
        except KafkaError as e:
            logger.error(f"Не удалось создать Confluent Kafka Producer: {e}")
            raise
    return _producer_instance


def send_calculation_request(
    task_id: str,
    start_port_id: int,
    end_port_id: int,
    vessel_speed_knots: Optional[float] = None,  # Новый параметр
) -> bool:
    message_payload = {
        "task_id": task_id,
        "start_port_id": start_port_id,
        "end_port_id": end_port_id,
    }
    if vessel_speed_knots is not None:  # Добавляем скорость, если она задана
        message_payload["vessel_speed_knots"] = vessel_speed_knots

    try:
        message_value_bytes = json.dumps(message_payload).encode("utf-8")
    except TypeError as e:
        logger.error(
            f"Ошибка сериализации сообщения в JSON: {e}, полезная нагрузка: {message_payload}"
        )
        return False

    producer = get_kafka_producer()

    try:
        producer.produce(
            topic=REQUEST_TOPIC,
            value=message_value_bytes,
            key=str(task_id).encode("utf-8"),
            callback=_delivery_report,
        )

        producer.poll(0)

        remaining_messages = producer.flush(timeout=10)

        if remaining_messages == 0:
            logger.info(
                f"Сообщение для task_id {task_id} успешно поставлено в очередь и отправлено (после flush)."
            )
            return True
        else:
            logger.error(
                f"Не удалось отправить сообщение для task_id {task_id} в течение {10} секунд. "
                f"Осталось сообщений в очереди: {remaining_messages}"
            )
            return False

    except KafkaError as e:
        logger.error(
            f"Ошибка Kafka при попытке отправить сообщение (produce или flush): {e}"
        )
        return False
    except BufferError as e:
        logger.error(
            f"Внутренняя очередь Kafka продюсера переполнена: {e}. Попытка протолкнуть сообщения."
        )
        producer.flush(5)
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке сообщения в Kafka: {e}")
        return False
