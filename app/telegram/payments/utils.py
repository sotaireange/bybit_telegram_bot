import asyncio


from app.db.services.redis_db import RedisClient
from app.db.models import Run


async def change_run(redis_client:RedisClient,user_id:int):
    user_run=await redis_client.get_is_run(user_id)
    if user_run==Run.HEDGE_SUB:
        await redis_client.set_is_run(user_id,Run.ACTIVE)
    return