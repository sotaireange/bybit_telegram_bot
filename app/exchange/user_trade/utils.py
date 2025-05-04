import logging
from decimal import Decimal
from typing import Union, Dict,Hashable,List



logger=logging.getLogger('trading')


async def send_notification(user_id:int, order:Dict,coin:Hashable):
    try:
        logger.info(f'User_id: {user_id}, coin {coin} order: {order['orderStatus']} - {order["orderId"]} {order['createType']}')
    except Exception as e:
        logger.error(e)

def round_step_size(quantity: Union[float, Decimal], step_size: Union[float, Decimal]) -> float:
    quantity = Decimal(str(quantity))
    return float(quantity - quantity % Decimal(str(step_size)))

def proof_result(data: Union[Dict,List], type_data) -> bool:
    return (isinstance(data,type_data) and len(data)>0)

def safe_float(value):
    if value is '' or value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0
