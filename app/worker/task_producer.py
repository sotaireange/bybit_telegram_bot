import logging
import asyncio

from faststream.redis import RedisBroker, RedisMessage
from faststream import FastStream

from app.exchange.user_trade.start_trade import trading

from app.common.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Task,TaskStatus
from app.db.models import TaskMessage,TelegramMessage


from app.worker.broker import subscribe_to_tasks,create_redis_broker



logger = logging.getLogger('worker')

class TaskWorker:
    def __init__(self):
        self.broker:RedisBroker
        self.app:FastStream
        self.session = AsyncSessionLocal


    async def init(self):
        self.broker = await create_redis_broker(settings.REDIS_URL)
        self.app = FastStream(broker=self.broker)
        logger.info('INIT')
        subscribe_to_tasks(self.broker,self.process_task)


    async def process_task(self,msg: TaskMessage):
        try:
            logger.info(f"Task Taked: {msg}")
            task_id=msg.task_id
            async with self.session() as session:
                task=await Task.get_task(session=session, id=task_id)
            result_data={}
            try:
                await self._execute_task(task)
                result_data.update({'status': TaskStatus.COMPLETED,
                                    'result': 'Корректно завершилось'})
            except Exception as e:
                logger.error(f"Task {task_id} Failed")
                result_data.update({'error':str(e),
                                    'status': TaskStatus.FAILED,
                                    'result': 'Ошибка'})
            finally:
                async with self.session() as session:
                    await Task.update(session=session,task_id=task_id,**result_data)



            logger.info(f"Task {task.id} done")

        except Exception as e:
            logger.exception(f"Error {str(e)}")



    async def _execute_task(self, task: Task):
        logger.info(f"Task {task.user_id} started")
        await trading(user_id=task.user_id)
        return True




    async def run(self):
        await self.app.run()




