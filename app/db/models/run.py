from enum import Enum



class Run(str, Enum):
    ACTIVE = "active"
    HEDGE = "hedge"
    HEDGE_SUB='hedge_sub'
    OFF = "off"