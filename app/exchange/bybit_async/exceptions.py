class BybitApiError(Exception):
    """Исключение для ошибок, связанных с API Bybit."""
    def __init__(self, data):
        self.ret_code = data['retCode']
        self.ret_msg = data['retMsg']
        super().__init__(f"Bybit API Error - retCode: {self.ret_code}, retMsg: {self.ret_msg}")
