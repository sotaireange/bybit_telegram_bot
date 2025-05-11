from enum import Enum



class Run(str, Enum):
    ACTIVE = "active"
    HEDGE = "hedge"
    OFF = "off"