import logging
from typing import Dict, List, Optional, Union,Hashable
from datetime import datetime
import asyncio
import random

from app.exchange.bybit_async import BybitRequester
from app.exchange.bybit_async import BybitApiError

logger=logging.getLogger('trading')

#TODO: ПЕРЕСМОТРЕТЬ КАКИЕ ДАННЫЕ ВОЗВРАЩАЮТСЯ ЕСЛИ БОЛЬШАЯ ОШИБКА

async def place_order(
        bybit_requester: BybitRequester,
        coin:Hashable,
        amount:float,
        buy:bool,
        tp_price:float=0,
        sl_price:float=0
) -> Optional[Dict]:

    if buy not in {True, False}:
        raise ValueError("The 'buy' parameter must be either True or False")

    if amount <= 0:
        raise ValueError("The 'amount' parameter must be greater than 0.")
    if tp_price <= 0 and sl_price<=0:
        raise ValueError("The 'tp_price' parameter must be greater than 0.")

    order_data = {
            'category': 'linear',
            'symbol': coin,
            'orderType': 'Market',
            'side': 'Buy' if buy else "Sell",
            'qty': str(amount),
            'takeProfit': str(tp_price) if tp_price else None,
            'stopLoss': str(sl_price) if sl_price else None,
            "timeInForce":"GTC",
            "positionIdx": 1 if buy else 2


    }
    response={}
    try:
        response = (await bybit_requester.send_signed_request(
            method='POST',
            endpoint='/v5/order/create',
            params=order_data
        ))
    except BybitApiError as e:
        logger.error(f'Error in place order\n'
                     f'Data: {order_data}\nError: {e}')
    except Exception as e:
        logger.error(e,stack_info=True)

    finally:
        return response



async def set_leverage(bybit_requester: BybitRequester,
                       coin: Union[Hashable,str],
                       leverage: float
                       ):

    data = {
        'category': 'linear',
        'symbol': coin,
        'buyLeverage': str(leverage),
        'sellLeverage': str(leverage)
    }

    try:
        response = await bybit_requester.send_signed_request(
            method='POST',
            endpoint='/v5/position/set-leverage',
            params=data
        )
    except BybitApiError as e:
        pass
        #logger.debug(f'{coin} failed set leverage {e}')
    except Exception as e:
        logger.exception(e)




async def switch_position_mode(bybit_requester: BybitRequester) -> Optional[bool]:
    data = {
        'category': 'linear',
        'coin': 'USDT',
        'mode': 3
    }

    # Send the request and handle potential errors
    try:
        await bybit_requester.send_signed_request(
            method='POST',
            endpoint='/v5/position/switch-mode',
            params=data
        )
    except BybitApiError as e:
        logger.error(f'Error switch position\n {e}')
        return
    except Exception as e:
        logger.exception(e)
        return

    return True



async def get_order(bybit_requester: BybitRequester,
                    coin: Hashable,
                    id: Optional[str] = None,
                    history: Optional[bool]=False,
                    limit: int = 2
                    ) -> List[Dict]:
    data = {'category': 'linear', 'symbol': coin}
    if id:
        data['orderId'] = id
    data['limit'] = limit

    if history:
        endpoint='/v5/order/history'
    else:
        endpoint='/v5/order/realtime'

    response=[{}]

    try:
        response = (await bybit_requester.send_signed_request(
            method='GET',
            endpoint=endpoint,
            params=data
        ))['result']['list']
    except BybitApiError as e:
        logger.error(f'Error get order \nData: {data}\n'
                     f'Endpoint {e}\n {e}')
    except Exception as e:
        logger.error(f'Error get order \nData: {data}\n'
                     f'Endpoint {endpoint}\n {e}')
    finally:
        return response



async def get_positions(bybit_requester: BybitRequester,
                        coin: Hashable
                        ) -> List[Dict]:

    data = {'category': 'linear',
            'symbol': coin}

    response=[{}]
    try:
        response = (await bybit_requester.send_signed_request(
            method='GET',
            endpoint='/v5/position/list',
            params=data
        )).get('result',{}).get('list',[])
    except BybitApiError as e:
        logger.error(f'Error get positions \nData: {data}\n'
                     f'{e}')

    except Exception as e:
        logger.exception(e)

    finally:
        return response

async def get_instrument_info(bybit_requester:BybitRequester) -> Optional[Dict]:
    data={'category': 'linear'}

    try:
        response = await bybit_requester.send_public_request(endpoint='/v5/market/instruments-info',params=data)
    except BybitApiError as e:
        logger.error(f'Error get instrument position \nData: {data}\n'
                     f'{e}')
        return
    except Exception as e:
        logger.exception(e)
        return
    return response.get('result',{}).get('list',{})


async def get_api_permissions(bybit_requester:BybitRequester) -> Dict:
    result={}
    try:
        result=(await bybit_requester.send_signed_request(
            method='GET',
            endpoint='/v5/user/query-api',
            params={}
        ))['result']
    except BybitApiError as e:
        logger.error(f'Error get api permisions\n'
                     f'Error: {e}')
    except Exception as e:
        logger.exception(f'Error get permissions {e}')
    finally:
        return result


async def get_balance(bybit_requester:BybitRequester) -> Dict:
    data={'accountType': 'UNIFIED',"coin": 'USDT'}
    result={}
    try:
        response = await bybit_requester.send_signed_request(method='GET',endpoint='/v5/account/wallet-balance',params=data)
        result = response.get('result',{}).get('list',[{}])
        result=result[0] if result else {}

    except BybitApiError as e:
        logger.error(f'Error: {e}')
    except Exception as e:
        logger.exception(f'Error get balance {e}')
    finally:
        return result


async def get_mark_price(bybit_requester:BybitRequester,
                         coin:Hashable
                         ) -> Optional[float]:
    data={'accountType': 'UNIFIED',"symbol": coin,'limit':1,'interval':1}
    try:
        response = await bybit_requester.send_public_request(endpoint='/v5/market/mark-price-kline',params=data)
    except BybitApiError as e:
        logger.error(f'Error get mark_price \nData: {data}\n'
                     f'{e}')
        return 0
    except Exception as e:
        logger.exception(e)
        return 0

    result=response['result']['list']
    return float(result[0][4]) if result else 0


async def get_all_position(bybit_requester:BybitRequester) -> List[Dict]:
    data = {
        'category': 'linear',
        'settleCoin':'USDT'
    }

    response=[{}]
    try:
        response = (await bybit_requester.send_signed_request(
            method='GET',
            endpoint='/v5/position/list',
            params=data
        ))['result']['list']
    except BybitApiError as e:
        logger.error(f'Error get all_positions \nData: {data}\n'
                     f'{e}')

    except Exception as e:
        logger.exception(e)

    finally:
        return response



async def close_order(bybit_requester:BybitRequester, position:Dict) -> Dict:
    side='Buy' if position['side']=='Sell' else 'Sell'

    data = {
        'category': 'linear',
        'symbol':position['symbol'],
        'side': side,
        'orderType':'Market',
        'qty': position['size'],
        'marketUnit': 'baseCoin',
        'positionIdx': position['positionIdx'],
        'reduceOnly': True
    }

    response={}
    try:
        response =( await bybit_requester.send_signed_request(
            method='POST',
            endpoint='/v5/order/create',
            params=data
        ))['result']
    except BybitApiError as e:
        logger.error(f'Error get mark_price \nData: {data}\n'
                     f'{e}')

    except Exception as e:
        logger.exception(e)

    finally:
        return response



async def get_pnl_from_chunks(bybit_requester: BybitRequester, chunk:Dict[str,datetime]) -> List[Dict[str,str]]:
    await asyncio.sleep(random.random())
    data = {
        'category': 'linear',
        'limit':100,
        'startTime' : int(chunk['startTime'].timestamp())*1000,
        'endTime' : int(chunk['endTime'].timestamp())*1000
    }

    response=[{}]
    try:
        response = (await bybit_requester.send_signed_request(
            method='GET',
            endpoint='/v5/position/closed-pnl',
            params=data
        ))['result']['list']
    except BybitApiError as e:
        logger.error(f'Error switch position\n {e}')
    except Exception as e:
        logger.exception(e)
    finally:
        return response