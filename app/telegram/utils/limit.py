

class Limit:
    LEVERAGE=1,20
    BALANCE=30,70
    TAKE_PROFIT=5,30
    SIZE=1,5

    def __getattr__(self, name):
        name = name.upper()  # Приводим к верхнему регистру
        if hasattr(self, name):
            return getattr(self, name)
        raise AttributeError(f"'Limit' object has no attribute '{name}'")
