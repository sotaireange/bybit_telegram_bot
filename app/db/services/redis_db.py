import json
from redis.asyncio import Redis
from typing import Union,Optional,Dict, Hashable
import logging


from app.db.models import Run,CoinSettings,TradeSettings





class RedisClient:
    def __init__(self, redis: Redis):
        self.redis = redis

    GLOBAL_TRADE_SETTINGS_KEY = "global_trade_settings"

    DEFAULTS_TRADE = TradeSettings()



    GLOBAL_COIN_SETTINGS_KEY = "global_coin_settings"

    DEFAULTS_COIN = CoinSettings()


    async def initialize(self):
        exists = await self.redis.exists(self.GLOBAL_TRADE_SETTINGS_KEY)
        if not exists:
            await self.redis.hset(self.GLOBAL_TRADE_SETTINGS_KEY, mapping=self.DEFAULTS_TRADE.to_dict())

        exists = await self.redis.exists(self.GLOBAL_COIN_SETTINGS_KEY)
        if not exists:
            await self.redis.hset(self.GLOBAL_COIN_SETTINGS_KEY, mapping=self.DEFAULTS_COIN.to_dict())

    def get_key(self,field:str) -> str:
        if field in self.DEFAULTS_COIN.to_dict().keys():
            return self.GLOBAL_COIN_SETTINGS_KEY
        elif field in self.DEFAULTS_TRADE.to_dict().keys():
            return self.GLOBAL_TRADE_SETTINGS_KEY



    async def get_all_trade_settings(self) -> TradeSettings:
        result = await self.redis.hgetall(self.GLOBAL_TRADE_SETTINGS_KEY)
        result = {k: float(v) for k, v in result.items()}

        return TradeSettings(**result)

    async def get_all_coin_settings(self) -> CoinSettings:
        result = await self.redis.hgetall(self.GLOBAL_COIN_SETTINGS_KEY)
        result = {k: float(v) for k, v in result.items()}

        return CoinSettings(**result)

    async def get(self, field: str) -> float | None:
        key=self.get_key(field)
        value = await self.redis.hget(key, field)
        try:
            value=float(value)
        except:
            value=0.0
        return value
    async def set(self, field: str, value: Union[str,float]):
        key=self.get_key(field)
        await self.redis.hset(key, field, value)


    COINS_KEY = "coins"


    async def get_coins_with_delete_by_user(self,user_id:int) -> dict:
        result = await self.get_coins(f'{self.COINS_KEY}_{user_id}')
        await self.redis.hdel(f'{self.COINS_KEY}_{user_id}',*result.keys())
        return result

    async def save_coin_by_user(self,data:dict,user_id:int):
        await self.save_coins(data,f'{self.COINS_KEY}_{user_id}')

    async def get_coins(self,key:str=COINS_KEY) -> dict:
        res = await self.redis.hgetall(key)
        return {k: json.loads(v) for k, v in res.items()}

    async def save_coins(self, data: dict, key:str=COINS_KEY):
        existing_keys = set(await self.redis.hkeys(key))

        new_keys = set(data.keys())

        keys_to_delete = existing_keys - new_keys
        if keys_to_delete:
            await self.redis.hdel(key, *keys_to_delete)

        json_data = {k: json.dumps(v) for k, v in data.items()}
        await self.redis.hset(key, mapping=json_data)

    COIN_INFO_KEY = "coins_info"

    async def get_all_coins_info(self) -> dict:
        res = await self.redis.hgetall(self.COIN_INFO_KEY)
        return {k: json.loads(v) for k, v in res.items()}

    async def get_coin_info(self,symbol:str) -> dict:
        res = await self.redis.hget(self.COIN_INFO_KEY,symbol)
        return {symbol:json.loads(res)}

    async def save_coins_info(self, data: dict):
        json_data = {k: json.dumps(v) for k, v in data.items()}
        await self.redis.hset(self.COIN_INFO_KEY, mapping=json_data)


    IS_RUN_KEY='is_run'

    async def get_is_run(self, user_id: int) -> Run:
        data = await self.redis.get(f'{self.IS_RUN_KEY}:{user_id}')
        if data is None:
            await self.set_is_run(user_id,Run.OFF)
            data = await self.redis.get(f'{self.IS_RUN_KEY}:{user_id}')
        return Run(json.loads(data)) if data else Run.OFF

    async def set_is_run(self, user_id: int, flag:Run):
        await self.redis.set(f'{self.IS_RUN_KEY}:{user_id}', json.dumps(flag))

    async def get_all_is_run(self) -> Dict[int, Run]:
        keys = await self.redis.keys(f'{self.IS_RUN_KEY}:*')
        result = {}
        for key in keys:
            try:
                user_id = int(key.split(':')[1])
                result[user_id] = await self.get_is_run(user_id)
            except (IndexError, ValueError):
                continue
        return result


    PRICES='prices'

    async def save_mark_price_coins(self,data: Dict) -> None:
        await self.redis.hset(self.PRICES,mapping=data)


    async def get_mark_price_coin(self,symbol: Hashable) -> float:
        value=await self.redis.hget(self.PRICES,symbol)
        try:
            value = float(value)
        except ValueError:
            logging.error(f'Could not convert {symbol} to float')
            value=0.0
        finally:
            return value
