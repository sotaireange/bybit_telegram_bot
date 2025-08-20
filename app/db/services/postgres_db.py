from datetime import timedelta,datetime,timezone
import logging
from typing import Optional,Dict,Sequence,List
from aiogram.types import User as UserTelegram

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update,delete
from sqlalchemy.orm import selectinload


from app.db.models import User,Notification,UserAPI


logger=logging.getLogger('system')

async def get_all_users(db:AsyncSession) -> Sequence[User]:
    result = await db.execute(select(User))
    return result.scalars().all()
async def get_user(db: AsyncSession, user_id: int) -> User:
    result = await db.execute(select(User).options(selectinload(User.apis))
                              .where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_one_api(db:AsyncSession,user_id:int,name:str) -> UserAPI:
    stmt = select(UserAPI).where(UserAPI.user_id == user_id)

    if name is not None:
        stmt = stmt.where(UserAPI.name == name)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()
async def get_user_apis(db:AsyncSession,user_id:int) -> Sequence[UserAPI]:
    stmt = select(UserAPI).where(UserAPI.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

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



async def add_user_api(db: AsyncSession, user_id: int, name: str) -> UserAPI:
    new_api = UserAPI(user_id=user_id, name=name)
    db.add(new_api)
    await db.commit()
    await db.refresh(new_api)
    return new_api


async def update_user_api(
        db: AsyncSession,
        user_id: int,
        new_api: str = None,
        new_secret: str = None,
        name: str = None,
        run:bool=None,
        single_api_mode: bool = False
) -> bool:

    if single_api_mode:
        result = await db.execute(
            select(UserAPI).where(UserAPI.user_id == user_id)
        )
        record = result.scalars().first()
        if not record:
            return False

        if new_api is not None:
            record.api = new_api
        if new_secret is not None:
            record.secret = new_secret

        await db.commit()
        return True

    else:
        if not name:
            raise ValueError("old API IS REQUIRED")

        stmt = (
            update(UserAPI)
            .where(UserAPI.user_id == user_id)
            .where(UserAPI.name == name)
            .execution_options(synchronize_session="fetch")
        )

        values = {}
        if new_api is not None:
            values["api"] = new_api
        if new_secret is not None:
            values["secret"] = new_secret
        if run is not None:
            values['run']=run

        if not values:
            return False

        result = await db.execute(stmt.values(**values))
        await db.commit()
        rows = result.rowcount or 0
        return rows > 0


async def delete_user_api(db: AsyncSession, user_id: int, name: str) -> bool:
    result = await db.execute(
        delete(UserAPI)
        .where(UserAPI.user_id == user_id)
        .where(UserAPI.name == name)
    )
    await db.commit()
    rows = result.rowcount or 0
    return rows > 0