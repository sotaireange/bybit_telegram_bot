import logging
import asyncio
from typing import Dict
from aiohttp.client_exceptions import ClientConnectorDNSError
import aiohttp
from .exceptions import BybitApiError

from app.common.config import settings

logger=logging.getLogger('trading')


API_RETRY_COUNT = settings.API_RETRY

SKIP_RET_CODE= [0,10001,110043]#[0,10001,110043,30209,30208] # SKIP RET CODE, IT WILL PASS WHEN RAISE RET MSG

def calculate_backoff(retrycount, max_retries):

    return (max_retries - retrycount) ** 2 + 1


def validate_response(response: Dict,endpoing:str,params:Dict) -> None:
    if not isinstance(response, dict) or 'retCode' not in response or 'retMsg' not in response:
        raise ValueError(f"Unexpected response format: {response}")
    if response['retCode'] not in SKIP_RET_CODE:
        #logger.warning(f'Bybit Api Error {endpoing} \n Params {params}\nResponse {response}')
        raise BybitApiError(response)


def retrier_async(f):
    async def wrapper(*args, **kwargs):
        count = kwargs.pop("count", API_RETRY_COUNT)
        try:
            return await f(*args, **kwargs)
        except BybitApiError as ex:
            if ex.ret_code in SKIP_RET_CODE:
                return await f(*args, **kwargs)
            msg = f'{f.__name__}() returned exception: "{ex}". '
            if count > 0:
                count -= 1
                kwargs["count"] = count
                backoff_delay = calculate_backoff(count + 1, API_RETRY_COUNT)
                await asyncio.sleep(backoff_delay)
                # if msg:
                #     logger.debug(f"Retry attempt {API_RETRY_COUNT-count} endpoint={kwargs['endpoint']} \n"
                #                  f"Data: {kwargs}")
                return await wrapper(*args, **kwargs)
            else:
                logger.error(f"Connection error after all retries:\n"
                             f"{args} {kwargs}\n"
                             f"{msg}")
                raise ex


        except (ClientConnectorDNSError, aiohttp.ClientConnectionError) as e:
            msg = f'{f.__name__}() returned exception: "{e}". '
            if count > 0:
                count -= 1
                kwargs["count"] = count
                backoff_delay = calculate_backoff(count + 1, API_RETRY_COUNT)
                logger.warning(f"Connection error: {e}, retrying in {backoff_delay} seconds. Attempts left: {count}")
                await asyncio.sleep(backoff_delay*2)
                return await wrapper(*args, **kwargs)
            else:
                logger.error(f"Connection error after all retries:\n"
                             f"{msg}\n"
                             f"{args} {kwargs}")
                raise e

        except Exception as e:
            logger.error(f"Exception raised: {e} ")
            raise e

    return wrapper

