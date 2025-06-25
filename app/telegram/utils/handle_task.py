import asyncio
import logging

logger = logging.getLogger('system')


async def stop_task(task, name: str, timeout: int = 5):
    if task:
        task.cancel()
        try:
            await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timed out waiting for {name} task")