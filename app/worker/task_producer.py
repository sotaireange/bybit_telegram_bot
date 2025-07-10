import logging
import asyncio
import signal

from faststream.redis import RedisBroker
from faststream import FastStream



from app.exchange.user_trade.start_trade import trading

from app.common.config import settings
from app.db.database import AsyncSessionLocal
from app.db.models import Task,TaskStatus
from app.db.models import TaskMessage
from app.worker.broker import subscribe_to_tasks,create_redis_broker


from faststream.log import logger as faststream_logger

faststream_logger.setLevel(logging.WARNING)

logger = logging.getLogger('worker')

class TaskWorker:
    def __init__(self):
        self.broker:RedisBroker
        self.app:FastStream
        self.session = AsyncSessionLocal
        self._shutdown_event = asyncio.Event()
        self.tasks={}

    async def init(self):
        """Инициализация воркера с proper error handling"""
        try:
            self.broker = await create_redis_broker(settings.REDIS_URL)
            self.app = FastStream(broker=self.broker, logger=faststream_logger)

            @self.app.on_startup
            async def on_startup():
                logger.info("FastStream application started successfully")

            @self.app.on_shutdown
            async def on_shutdown():
                logger.info("FastStream application shutting down")


            # Регистрация подписчиков
            subscribe_to_tasks(self.broker, self.process_task)

            # Настройка graceful shutdown
            self._setup_signal_handlers()

            logger.info('TaskWorker initialized successfully')

        except Exception as e:
            logger.error(f"Failed to initialize TaskWorker: {e}")
            raise


    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            asyncio.create_task(self.shutdown())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)




    async def process_task(self, msg: TaskMessage):
        """Обработка задачи с улучшенной обработкой ошибок"""
        task_id = msg.task_id
        logger.info(f"Processing task: {task_id}")

        try:
            async with self.session() as session:
                task = await Task.get_task(session=session, id=task_id)
                if not task:
                    logger.error(f"Task {task_id} not found in database")
                    return
                await Task.update(session=session, task_id=task_id,status=TaskStatus.PROCESSING)

            task=asyncio.create_task(self.handle_task(task=task))
            self.tasks[task_id]=task
        except Exception as e:
            logger.exception(f"Critical error processing task {task_id}: {e}")
            raise

    async def _execute_task(self, task: Task):
        logger.info(f"Executing task for user {task.user_id}")

        try:
            await trading(user_id=task.user_id)
            return True
        except Exception as e:
            logger.error(f"Trading execution failed for user {task.user_id}: {e}")
            raise

    async def handle_task(self,task):
        task_id=task.id
        result_data = {}
        try:
            # Выполнение задачи
            await self._execute_task(task)
            result_data.update({
                'status': TaskStatus.COMPLETED,
                'result': 'Корректно завершилось'
            })
            logger.info(f"Task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            result_data.update({
                'error': str(e),
                'status': TaskStatus.FAILED,
                'result': 'Ошибка'
            })

            # Обновление статуса задачи
        async with self.session() as session:
            await Task.update(session=session, task_id=task_id, **result_data)

        self.tasks.pop(task_id)
    async def health_check(self):
        try:
            if self.broker:
                return (await self.broker.ping(timeout=3))
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def restart_broker_if_needed(self):
        if not await self.health_check():
            logger.warning("Broker health check failed, attempting restart...")
            try:
                if self.broker:
                    await self.broker.close()

                self.broker = await create_redis_broker(settings.REDIS_URL)
                subscribe_to_tasks(self.broker, self.process_task)

                logger.info("Broker restarted successfully")
            except Exception as e:
                logger.error(f"Failed to restart broker: {e}")
                raise
    async def run(self):
        """Запуск воркера с мониторингом здоровья"""
        health_check_task = asyncio.create_task(self._health_check_loop())
        try:
            await self.app.run()

        except Exception as e:
            logger.error(f"Worker run failed: {e}")
            raise
        finally:
            health_check_task.cancel()
            await self.shutdown()

    async def _health_check_loop(self):
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(60)  # Проверка каждую минуту
                if not await self.health_check():
                    await self.restart_broker_if_needed()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def shutdown(self):
        """Graceful shutdown воркера"""
        logger.info("Shutting down TaskWorker...")
        self._shutdown_event.set()

        try:
            if self.app:
                await self.app.stop()
            if self.broker:
                await self.broker.close()
            logger.info("TaskWorker shutdown completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

        for task_id,task in self.tasks.items():
            try:
                task.cancel()
                await asyncio.wait_for(task, timeout=5)
            except asyncio.TimeoutError as er:
                logger.debug((f"{task.get_name()} took too long to cancel. {er}"))
            except asyncio.CancelledError as er:
                logger.debug((f"{task.get_name()} Cancelled. {er}"))




