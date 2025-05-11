from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from redis.asyncio import Redis
from .models import Base


from app.common.config import settings

import logging
logger=logging.getLogger('system')

engine = create_async_engine(
    settings.DB_URL,
    future=True,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)




r = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_async_session():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()



async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(lambda conn: Base.metadata.drop_all(conn, checkfirst=True))

async def close_databases():
    try:
        await r.close()
        await r.connection_pool.disconnect()

    except Exception as e:
        logger.error(f'Error while closing redis: {e}')
    try:
        await engine.dispose()
    except Exception as e:
        logger.error(f'Error while closing redis: {e}')
