from .base import TradingStrategy
from .auto_strategy import AutoTradingStrategy
from .manual_strategy import ManualTradingStrategy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..user_trade import TradeBot

def get_trading_strategy(mode: str, context: 'TradeBot') -> TradingStrategy:
    if mode == 'auto':
        return AutoTradingStrategy(context=context)
    elif mode == 'manually':
        return ManualTradingStrategy(context=context)
    else:
        raise ValueError(f"Неизвестный режим торговли: {mode}")