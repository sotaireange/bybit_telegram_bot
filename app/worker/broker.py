from typing import Dict, Any, Optional, Callable, Awaitable
import logging


from faststream.redis import RedisBroker
from app.db.models import TaskMessage,TelegramMessage

logger=logging.getLogger('worker')


async def create_redis_broker(redis_url: str) -> RedisBroker:
    broker = RedisBroker(redis_url)
    await broker.start()
    return broker


async def publish_task(broker: RedisBroker, task_message: TaskMessage) -> None:
    await broker.publish(task_message, "task_queue")


async def publish_telegram_message(broker: RedisBroker, telegram_message: TelegramMessage) -> None:
    await broker.publish(telegram_message, "telegram_message_queue")



def subscribe_to_tasks(broker: RedisBroker, handler: Callable[[TaskMessage], Awaitable[None]]):
    @broker.subscriber("task_queue")
    async def handle_task(msg: TaskMessage):
        logger.info('Receive task_queue')
        await handler(msg)


def subscribe_to_telegram_messages(broker: RedisBroker, handler: Callable[[TelegramMessage], Awaitable[None]]):
    @broker.subscriber("telegram_message_queue")
    async def handle_telegram_message(msg: TelegramMessage):
        logger.info('Receive telegram message_queue')
        await handler(msg)