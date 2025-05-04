from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from redis.asyncio import Redis
import os



from app.common.config import settings

engine = create_async_engine(
    settings.DB_URL,
    future=True,
    echo=False,  # Логгирование(нунжо убрать)
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()



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