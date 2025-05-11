import logging
from decimal import Decimal
from typing import Union, Dict,Hashable,List



logger=logging.getLogger('trading')

def improved_round_step_size(
        quantity: Union[float, Decimal],
        step_size: Union[float, Decimal],
        price: Union[float, Decimal],
        min_notional: Union[float, Decimal] = 5.0
) -> float:
    quantity = Decimal(str(quantity))
    step_size = Decimal(str(step_size))
    price = Decimal(str(price))
    min_notional = Decimal(str(min_notional))

    rounded_quantity = quantity - (quantity % step_size)

    notional_value = rounded_quantity * price

    if notional_value < min_notional:
        min_required_quantity = min_notional / price

        steps_needed = (min_required_quantity / step_size).quantize(Decimal('1'), rounding='ROUND_UP')
        rounded_quantity = steps_needed * step_size
    return float(rounded_quantity)


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
