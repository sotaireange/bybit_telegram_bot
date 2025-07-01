import logging
from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker
from faststream.redis import RedisBroker


from app.db.models import Task,TaskMessage

from app.worker.broker import publish_task


logger=logging.getLogger('system')

async def start_proccesing_trading(broker:RedisBroker,session_local:async_sessionmaker):
    try:
        async with session_local() as session:
            tasks=await Task.get_proccesing_tasks(session)
        for task in tasks:
            task_message=TaskMessage(task_id=task.id,task_type=task.type,user_id=task.user_id)
            await publish_task(broker,task_message)
        logger.info(f'{len(tasks)} Tasks success continue')
    except Exception as e:
        logger.error(f'Failed continue Tasks.\n'
                     f'Error : {e}')
