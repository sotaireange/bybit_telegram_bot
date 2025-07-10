from datetime import timedelta,datetime,timezone
import logging
from typing import Optional,Dict,Sequence
from aiogram.types import User as UserTelegram

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update


from app.db.models import User,Notification


logger=logging.getLogger('system')

async def get_all_users(db:AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User))
    return result.scalars().all()
async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_notification(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(Notification).where(Notification.user_id == user_id))
    return result.scalar_one_or_none()

async def update_bybit_subaccount_uid(db:AsyncSession, user_id: int, bybit_subaccount_uid:int):
    user = await get_user(db, user_id)
    if not user:
        logger.warning(f"User not found (id={user_id})")
        return

    result = await db.execute(
        select(User).where(User.bybit_sub_account_uid == bybit_subaccount_uid, User.id != user_id)
    )
    existing_uid_user = result.scalar_one_or_none()
    if existing_uid_user:
        logger.warning(f"bybit_sub_account_uid={bybit_subaccount_uid} уже привязан к другому пользователю (id={existing_uid_user.id})")
        return
    if user.bybit_sub_account_uid is not None:
        logger.warning(f"bybit_sub_account_uid уже установлен у пользователя {user_id}, обновление отклонено")
        return

    stmt = update(User).where(User.id == user_id).values(bybit_sub_account_uid=bybit_subaccount_uid)
    await db.execute(stmt)
    await db.commit()

async def update_bybit_uid(db:AsyncSession,user_id:int,bybit_uid:int) -> None:
    user = await get_user(db, user_id)
    if not user:
        logger.warning(f"User not found (id={user_id})")
        return

    if bybit_uid is not None:
        result = await db.execute(
            select(User).where(User.bybit_uid == bybit_uid, User.id != user_id)
        )
        existing_uid_user = result.scalar_one_or_none()
        if existing_uid_user:
            logger.warning(f"bybit_uid={bybit_uid} уже привязан к другому пользователю (id={existing_uid_user.id})")
            return

        if user.bybit_uid is not None:
            logger.warning(f"bybit_uid уже установлен у пользователя {user_id}, обновление отклонено")
            return

    stmt = update(User).where(User.id == user_id).values(bybit_uid=bybit_uid)
    await db.execute(stmt)
    await db.commit()

async def update_notification(db: AsyncSession, user_id: int, key: str):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user_id)
    )
    notification = result.scalar_one_or_none()

    if notification:
        if hasattr(notification, key):
            current_value = getattr(notification, key)
            setattr(notification, key, not current_value)

            await db.commit()
            await db.refresh(notification)
            return notification
        else:
            raise AttributeError(f"Поле '{key}' не существует в модели Notification")

    return None


async def update_user_fields(db: AsyncSession, user_id: int, fields_dict:Optional[Dict]=None,**kwargs) -> None:
    update_values = {}
    if fields_dict:
        update_values.update(fields_dict)
    update_values.update(kwargs)



    user = await get_user(db, user_id)
    if not user:
        logger.warning(f"User not found (id={user_id})")
        return


    stmt = update(User).where(User.id == user_id).values(**update_values)
    await db.execute(stmt)
    await db.commit()


async def extend_subscription_due_time(db: AsyncSession, user_id: int, time:int,days=1) -> User:
    user = await get_user(db, user_id)
    if user:
        time=datetime.fromtimestamp(time, tz=timezone.utc)
        user.last_sub_time=time
        now=datetime.now(timezone.utc)
        target_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now.time() > target_time.time():
            target_time = target_time + timedelta(days=1)
        user.sub_until = target_time
        await db.commit()
        await db.refresh(user)
        return user
    else:
        logger.warning(f"Haven't user (id={user_id}")


async def extend_subscription(db: AsyncSession, user_id: int, days: int) -> User:
    user = await get_user(db, user_id)
    if user:
        now=datetime.now(timezone.utc)
        # user.last_sub_time=now
        target_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
        if now.time() > target_time.time():
            target_time = target_time + timedelta(days=1)
        user.sub_until = target_time
        await db.commit()
        await db.refresh(user)
        return user
    else:
        logger.warning(f"Haven't user (id={user_id}")


async def unsubscribe(db: AsyncSession, user_id: int) -> None:
    user = await get_user(db, user_id)
    if user:
        sub_until=datetime.now(timezone.utc)
        user.sub_until = sub_until
        await db.commit()
        await db.refresh(user)
        return user
    else:
        logger.warning(f"Haven't user (id={user_id}")

async def get_bybit_uid(db: AsyncSession):
    result=await db.execute(select(User.bybit_uid))
    return result.scalars().all()

async def create_new_user(db: AsyncSession, user_data: UserTelegram) -> User:
    existing_user =await get_user(db, user_data.id)

    if existing_user:
        return existing_user

    new_user = User(
        id=user_data.id,
        username=user_data.username,
        notification=Notification()\
    )


    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user