import asyncio

from app.worker.task_producer import TaskWorker

from app.common.loggers import setup_logging

import logging
logger=logging.getLogger('worker')


async def main():
    setup_logging()
    logger.info("Starting system")
    worker = TaskWorker()
    await worker.init()
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())