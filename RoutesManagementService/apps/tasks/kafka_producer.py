import json
import logging
import os
import socket  # Для получения имени хоста, полезно для client.id
from typing import Optional

from confluent_kafka import KafkaError, Message, Producer  # Message для типа в callback

logger = logging.getLogger(__name__)

KAFKA_BROKER_URL = os.getenv("KAFKA_BROKER_URL", "kafka:9092")
REQUEST_TOPIC = os.getenv("KAFKA_REQUEST_TOPIC", "route_calculation_requests")

_producer_instance: Optional[Producer] = None


def _delivery_report(err: Optional[KafkaError], msg: Optional[Message]):
    """
    Вызывается один раз для каждого сообщения, доставленного (или не доставленного) брокеру.
    """
    if err is not None:
        logger.error(f"Ошибка доставки сообщения в Kafka: {err}")
    else:
        if msg is not None:  # Проверка на None для msg
            logger.info(
                f"Сообщение успешно доставлено в топик {msg.topic()} "
                f"раздел [{msg.partition()}] с offset {msg.offset()}"
            )
        else:  # Этого не должно происходить если err is None, но для безопасности
            logger.warning(
                "Delivery report вызван без ошибки, но объект сообщения отсутствует."
            )


def get_kafka_producer() -> Producer:
    global _producer_instance
    if _producer_instance is None:
        conf = {
            "bootstrap.servers": KAFKA_BROKER_URL,
            "client.id": socket.gethostname(),  # Идентификатор клиента
            # 'acks': 'all', # Гарантия доставки (все реплики подтвердили запись)
            # 'retries': 3, # Количество попыток отправки
            # 'retry.backoff.ms': 1000, # Пауза между попытками
            # Настройки для повышения надежности (можно настроить по необходимости)
            "enable.idempotence": "true",  # Гарантирует, что сообщения не будут дублироваться при повторных отправках (требует acks='all')
            "acks": "all",  # Для idempotence acks должен быть 'all'
            "message.timeout.ms": 30000,  # Максимальное время ожидания доставки сообщения (включая повторы)
            # 'linger.ms': 5, # Задержка перед отправкой батча (увеличивает пропускную способность за счет небольшой задержки)
            # 'compression.type': 'lz4', # Тип сжатия (gzip, snappy, lz4, zstd)
        }
        try:
            _producer_instance = Producer(conf)
            logger.info(
                f"Confluent Kafka Producer сконфигурирован для {KAFKA_BROKER_URL}"
            )
        except KafkaError as e:
            logger.error(f"Не удалось создать Confluent Kafka Producer: {e}")
            raise  # Передаем исключение дальше, чтобы приложение знало о проблеме
    return _producer_instance


def send_calculation_request(
    task_id: str, start_port_id: int, end_port_id: int
) -> bool:
    message_payload = {
        "task_id": task_id,
        "start_port_id": start_port_id,
        "end_port_id": end_port_id,
    }
    # Сериализуем сообщение в JSON строку, а затем в байты
    try:
        message_value_bytes = json.dumps(message_payload).encode("utf-8")
    except TypeError as e:
        logger.error(
            f"Ошибка сериализации сообщения в JSON: {e}, полезная нагрузка: {message_payload}"
        )
        return False

    producer = get_kafka_producer()

    try:
        # produce() неблокирующий. Он помещает сообщение во внутреннюю очередь и немедленно возвращается.
        # delivery_report будет вызван асинхронно.
        producer.produce(
            topic=REQUEST_TOPIC,
            value=message_value_bytes,
            key=str(task_id).encode(
                "utf-8"
            ),  # Ключ помогает с партицированием, если нужно. Task_id - хороший кандидат.
            callback=_delivery_report,  # Необязательно для каждой отправки, если не нужен детальный лог на каждое сообщение
        )

        # Важно: poll() нужен для обслуживания очереди доставки и вызова колбэков.
        # Если не вызывать poll(), колбэки не будут срабатывать.
        # Для простого случая отправки и забывания, можно poll(0) не вызывать часто.
        # Но для гарантированной обработки колбэков или если есть ожидание `flush`, poll важен.
        producer.poll(0)  # Неблокирующий вызов для обработки событий в очереди

        # Для имитации поведения `future.get()` из kafka-python (ожидание подтверждения),
        # используем `flush()`. Это заблокирует выполнение, пока все сообщения
        # не будут отправлены (или не истечет таймаут).
        # Возвращает количество сообщений, ожидающих доставки. 0 означает, что все отправлено.
        remaining_messages = producer.flush(timeout=10)  # Таймаут в секундах

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
            # В этом случае delivery_report может еще не сработать с ошибкой,
            # но flush вернул > 0, что указывает на проблему.
            return False

    except KafkaError as e:
        # Эта ошибка может возникнуть, если, например, очередь продюсера переполнена (queue.buffering.max.messages)
        logger.error(
            f"Ошибка Kafka при попытке отправить сообщение (produce или flush): {e}"
        )
        return False
    except BufferError as e:  # Очередь продюсера переполнена
        logger.error(
            f"Внутренняя очередь Kafka продюсера переполнена: {e}. Попробуйте позже или увеличьте queue.buffering.max.messages."
        )
        # Можно вызвать poll() или flush() чтобы попытаться освободить очередь перед повторной попыткой
        producer.flush(5)  # Попытка протолкнуть сообщения
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке сообщения в Kafka: {e}")
        return False
