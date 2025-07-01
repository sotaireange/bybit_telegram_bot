from typing import Dict, Any, Optional, Callable, Awaitable
import logging
import asyncio

from faststream.redis import RedisBroker
from app.db.models import TaskMessage,TelegramMessage

logger=logging.getLogger('worker')


async def create_redis_broker(redis_url: str) -> RedisBroker:
    """Создание Redis брокера с улучшенными настройками подключения"""
    broker = RedisBroker(
        redis_url,
        max_connections=20,
        retry_on_timeout=True,
        log_level=logging.INFO,
        socket_connect_timeout=10,
        socket_keepalive=True,
        health_check_interval=30,
    )

    await broker.connect()

    return broker


async def publish_task(broker: RedisBroker, task_message: TaskMessage, max_retries: int = 3) -> bool:
    """Публикация задачи с retry механизмом"""
    for attempt in range(max_retries):
        try:
            await broker.publish(task_message, "task_queue")
            logger.info(f"Task published successfully: {task_message.task_id}")
            return True
        except Exception as e:
            logger.warning(f"Publish attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f'Failed to publish task after {max_retries} attempts: {e}')
                return False


async def publish_telegram_message(broker: RedisBroker, telegram_message: TelegramMessage, max_retries: int = 3) -> bool:
    for attempt in range(max_retries):
        try:
            await broker.publish(telegram_message, "telegram_message_queue")
            return True
        except Exception as e:
            logger.warning(f"Telegram message publish attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error(f'Failed to publish telegram message after {max_retries} attempts: {e}')
                return False


def subscribe_to_tasks(broker: RedisBroker, handler: Callable[[TaskMessage], Awaitable[None]]):
    @broker.subscriber("task_queue",retry=True)
    async def handle_task(msg: TaskMessage):
        logger.info('Receive task_queue')
        await handler(msg)


def subscribe_to_telegram_messages(broker: RedisBroker, handler: Callable[[TelegramMessage], Awaitable[None]]):
    @broker.subscriber("telegram_message_queue",retry=True)
    async def handle_telegram_message(msg: TelegramMessage):
        #logger.info('Receive telegram message_queue')
        await handler(msg)